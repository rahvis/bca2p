"""Experimental distributed substrate interfaces and models."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from bca2p.core import AgentProfile, ArtifactRef, SignalEnvelope, SignalMode
from bca2p.registry.store import FileRegistryStore, InMemoryRegistryStore, RegistryStore


@dataclass(frozen=True, slots=True)
class TopologyEdge:
    """Relationship between two routable nodes in the substrate."""

    source: str
    target: str
    directed: bool = True
    scopes: tuple[str, ...] = ()
    weight: float = 1.0

    def key(self) -> str:
        return f"{self.source}->{self.target}"


@dataclass(slots=True)
class SignalLogEntry:
    """Persisted signal event for replay and resilience analysis."""

    signal: SignalEnvelope
    status: str
    node_id: str
    reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal": self.signal.to_dict(),
            "status": self.status,
            "node_id": self.node_id,
            "reason": self.reason,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SignalLogEntry":
        return cls(
            signal=SignalEnvelope.from_dict(data["signal"]),
            status=data["status"],
            node_id=data["node_id"],
            reason=data.get("reason"),
            metadata=dict(data.get("metadata", {})),
        )


class TopologyIndex(Protocol):
    """Persistent store for communication-topology edges."""

    def save_edge(self, edge: TopologyEdge) -> None:
        """Persist an edge."""

    def neighbors(self, node_id: str) -> list[TopologyEdge]:
        """Return outgoing neighbors for a node."""

    def list_edges(self) -> list[TopologyEdge]:
        """List all known edges."""


class SignalLog(Protocol):
    """Persistent store for routed signal events."""

    def append(self, entry: SignalLogEntry) -> None:
        """Persist a signal log entry."""

    def list(self) -> list[SignalLogEntry]:
        """Return all signal log entries."""


class ArtifactStore(Protocol):
    """Storage interface for artifact payloads referenced by signals."""

    def put(self, artifact: ArtifactRef, payload: bytes) -> ArtifactRef:
        """Store the artifact payload and return the normalized artifact ref."""

    def get(self, artifact_id: str) -> bytes | None:
        """Retrieve an artifact payload by its ID."""


class MeshTransport(Protocol):
    """Transport substrate for direct node-to-node communication."""

    def register_node(self, node_id: str, handler: Any) -> None:
        """Register a routable node handler."""

    async def send(self, signal: SignalEnvelope, *, node_id: str) -> list[SignalEnvelope]:
        """Send a signal directly to a node."""

    def isolate(self, node_id: str) -> None:
        """Simulate a partition affecting the target node."""

    def heal(self, node_id: str) -> None:
        """Heal a simulated partition."""


@dataclass
class InMemoryTopologyIndex:
    """In-memory topology persistence."""

    _edges: dict[str, TopologyEdge] | None = None

    def __post_init__(self) -> None:
        if self._edges is None:
            self._edges = {}

    def save_edge(self, edge: TopologyEdge) -> None:
        self._edges[edge.key()] = edge

    def neighbors(self, node_id: str) -> list[TopologyEdge]:
        return [edge for edge in self._edges.values() if edge.source == node_id]

    def list_edges(self) -> list[TopologyEdge]:
        return list(self._edges.values())


@dataclass
class FileTopologyIndex:
    """JSON-backed topology persistence."""

    path: str | Path

    def __post_init__(self) -> None:
        self._path = Path(self.path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write([])

    def save_edge(self, edge: TopologyEdge) -> None:
        edges = {stored.key(): stored for stored in self.list_edges()}
        edges[edge.key()] = edge
        self._write(list(edges.values()))

    def neighbors(self, node_id: str) -> list[TopologyEdge]:
        return [edge for edge in self.list_edges() if edge.source == node_id]

    def list_edges(self) -> list[TopologyEdge]:
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        return [TopologyEdge(**entry) for entry in payload]

    def _write(self, edges: list[TopologyEdge]) -> None:
        payload = [
            {
                "source": edge.source,
                "target": edge.target,
                "directed": edge.directed,
                "scopes": list(edge.scopes),
                "weight": edge.weight,
            }
            for edge in edges
        ]
        self._path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


@dataclass
class InMemorySignalLog:
    """In-memory persistence for signal delivery outcomes."""

    _entries: list[SignalLogEntry] | None = None

    def __post_init__(self) -> None:
        if self._entries is None:
            self._entries = []

    def append(self, entry: SignalLogEntry) -> None:
        self._entries.append(entry)

    def list(self) -> list[SignalLogEntry]:
        return list(self._entries)


@dataclass
class FileSignalLog:
    """JSON-lines persistence for signal logs."""

    path: str | Path

    def __post_init__(self) -> None:
        self._path = Path(self.path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.touch(exist_ok=True)

    def append(self, entry: SignalLogEntry) -> None:
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.to_dict(), sort_keys=True) + "\n")

    def list(self) -> list[SignalLogEntry]:
        lines = [
            line.strip()
            for line in self._path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        return [SignalLogEntry.from_dict(json.loads(line)) for line in lines]


@dataclass
class InMemoryArtifactStore:
    """In-memory artifact payload storage."""

    _payloads: dict[str, bytes] | None = None

    def __post_init__(self) -> None:
        if self._payloads is None:
            self._payloads = {}

    def put(self, artifact: ArtifactRef, payload: bytes) -> ArtifactRef:
        self._payloads[artifact.artifact_id] = payload
        return artifact

    def get(self, artifact_id: str) -> bytes | None:
        return self._payloads.get(artifact_id)


@dataclass
class FileArtifactStore:
    """File-backed artifact payload storage."""

    directory: str | Path

    def __post_init__(self) -> None:
        self._directory = Path(self.directory)
        self._directory.mkdir(parents=True, exist_ok=True)

    def put(self, artifact: ArtifactRef, payload: bytes) -> ArtifactRef:
        (self._directory / artifact.artifact_id).write_bytes(payload)
        return artifact

    def get(self, artifact_id: str) -> bytes | None:
        path = self._directory / artifact_id
        if not path.exists():
            return None
        return path.read_bytes()


@dataclass
class InMemoryMeshTransport:
    """Mesh transport with partition simulation and local routing."""

    handlers: dict[str, Any] = field(default_factory=dict)
    isolated_nodes: set[str] = field(default_factory=set)

    def register_node(self, node_id: str, handler: Any) -> None:
        self.handlers[node_id] = handler

    async def send(self, signal: SignalEnvelope, *, node_id: str) -> list[SignalEnvelope]:
        if node_id in self.isolated_nodes:
            raise RuntimeError(f"Node {node_id!r} is partitioned")
        handler = self.handlers[node_id]
        result = handler(signal)
        if hasattr(result, "__await__"):
            result = await result  # type: ignore[assignment]
        if result is None:
            return []
        if isinstance(result, list):
            return result
        return [result]

    def isolate(self, node_id: str) -> None:
        self.isolated_nodes.add(node_id)

    def heal(self, node_id: str) -> None:
        self.isolated_nodes.discard(node_id)


@dataclass
class DistributedCoordinator:
    """SDK-owned substrate coordinating discovery, topology, storage, and routing."""

    registry_store: RegistryStore = field(default_factory=InMemoryRegistryStore)
    topology_index: TopologyIndex = field(default_factory=InMemoryTopologyIndex)
    signal_log: SignalLog = field(default_factory=InMemorySignalLog)
    artifact_store: ArtifactStore = field(default_factory=InMemoryArtifactStore)
    mesh_transport: MeshTransport = field(default_factory=InMemoryMeshTransport)

    def register_agent(self, profile: AgentProfile, handler: Any) -> AgentProfile:
        self.registry_store.save(profile)
        self.mesh_transport.register_node(profile.agent_id, handler)
        for scope in profile.scopes:
            self.topology_index.save_edge(
                TopologyEdge(source=scope, target=profile.agent_id, directed=True, scopes=(scope,))
            )
        return profile

    def connect(
        self,
        source: str,
        target: str,
        *,
        scopes: tuple[str, ...] = (),
        weight: float = 1.0,
    ) -> None:
        self.topology_index.save_edge(
            TopologyEdge(source=source, target=target, directed=True, scopes=scopes, weight=weight)
        )

    def store_artifact(self, artifact: ArtifactRef, payload: bytes) -> ArtifactRef:
        return self.artifact_store.put(artifact, payload)

    async def route(self, signal: SignalEnvelope) -> list[SignalEnvelope]:
        recipients = self._resolve_recipients(signal)
        responses: list[SignalEnvelope] = []
        if not recipients:
            self.signal_log.append(
                SignalLogEntry(
                    signal=signal,
                    status="dropped",
                    node_id=signal.recipient_scope,
                    reason="no_recipient",
                )
            )
            return responses

        for recipient in recipients:
            try:
                delivered = await self.mesh_transport.send(signal, node_id=recipient)
                self.signal_log.append(
                    SignalLogEntry(signal=signal, status="delivered", node_id=recipient)
                )
                responses.extend(delivered)
            except Exception as exc:  # noqa: BLE001
                self.signal_log.append(
                    SignalLogEntry(
                        signal=signal,
                        status="dropped",
                        node_id=recipient,
                        reason=str(exc),
                    )
                )
        return responses

    def replay_signal_log(self) -> list[SignalLogEntry]:
        return self.signal_log.list()

    def _resolve_recipients(self, signal: SignalEnvelope) -> list[str]:
        profiles = self.registry_store.list()
        if signal.mode == SignalMode.ENDOCRINE:
            return [
                profile.agent_id
                for profile in profiles
                if signal.recipient_scope in profile.scopes
            ]
        if signal.mode in {SignalMode.JUXTACRINE, SignalMode.SYNAPTIC}:
            return [edge.target for edge in self.topology_index.neighbors(signal.sender)]
        if signal.mode == SignalMode.PARACRINE:
            return [
                edge.target
                for edge in self.topology_index.neighbors(signal.sender)
                if signal.recipient_scope in edge.scopes or not edge.scopes
            ]
        if signal.receptor is not None:
            return [
                profile.agent_id
                for profile in profiles
                if any(receptor.receptor_id == signal.receptor for receptor in profile.receptors)
            ]
        return [
            profile.agent_id
            for profile in profiles
            if signal.recipient_scope in profile.scopes
        ]
