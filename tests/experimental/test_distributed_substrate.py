from __future__ import annotations

import asyncio
from pathlib import Path

from examples.distributed_mesh.app import run_distributed_example

from bca2p.core import AgentProfile, ArtifactRef, ReceptorSpec, SignalEnvelope, SignalMode
from bca2p.distributed import (
    DistributedCoordinator,
    FileArtifactStore,
    FileSignalLog,
    FileTopologyIndex,
    InMemoryMeshTransport,
    SignalLogEntry,
)
from bca2p.registry.store import FileRegistryStore


def _profile(agent_id: str) -> AgentProfile:
    return AgentProfile(
        agent_id=agent_id,
        scopes=["team"],
        receptors=[
            ReceptorSpec(
                receptor_id="task",
                accepted_modes=[SignalMode.PARACRINE, SignalMode.SYNAPTIC],
            )
        ],
    )


def test_distributed_example_and_partition_behavior() -> None:
    result = asyncio.run(run_distributed_example())

    assert result["delivered"] >= 1
    assert "dropped" in result["statuses"]


def test_file_backed_replay_after_restart(tmp_path: Path) -> None:
    registry = FileRegistryStore(tmp_path / "registry")
    topology = FileTopologyIndex(tmp_path / "topology.json")
    signal_log = FileSignalLog(tmp_path / "signal-log.jsonl")
    artifacts = FileArtifactStore(tmp_path / "artifacts")
    mesh = InMemoryMeshTransport()
    coordinator = DistributedCoordinator(
        registry_store=registry,
        topology_index=topology,
        signal_log=signal_log,
        artifact_store=artifacts,
        mesh_transport=mesh,
    )
    coordinator.register_agent(
        _profile("sender"),
        lambda signal: SignalEnvelope(
            signal_id=f"{signal.signal_id}:sender",
            mode=signal.mode,
            sender="sender",
            recipient_scope=signal.sender,
            receptor=signal.receptor,
            payload={"ok": True},
        ),
    )
    coordinator.register_agent(
        _profile("receiver"),
        lambda signal: SignalEnvelope(
            signal_id=f"{signal.signal_id}:receiver",
            mode=signal.mode,
            sender="receiver",
            recipient_scope=signal.sender,
            receptor=signal.receptor,
            payload={"ok": True},
        ),
    )
    coordinator.connect("sender", "receiver", scopes=("team",))
    coordinator.store_artifact(
        ArtifactRef(artifact_id="artifact-1", uri="memory://artifact-1"),
        b"payload",
    )

    asyncio.run(
        coordinator.route(
            SignalEnvelope(
                signal_id="log-1",
                mode=SignalMode.PARACRINE,
                sender="sender",
                recipient_scope="team",
                receptor="task",
                payload={"work": "x"},
            )
        )
    )

    restarted = DistributedCoordinator(
        registry_store=registry,
        topology_index=topology,
        signal_log=signal_log,
        artifact_store=artifacts,
        mesh_transport=mesh,
    )
    entries = restarted.replay_signal_log()

    assert entries
    assert isinstance(entries[0], SignalLogEntry)
    assert artifacts.get("artifact-1") == b"payload"
