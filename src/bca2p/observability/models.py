"""Trace, topology, and replay models for bca2p observability."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class RuntimeEventType(StrEnum):
    """Structured runtime event categories."""

    SIGNAL_EMITTED = "signal_emitted"
    SIGNAL_DELIVERED = "signal_delivered"
    SIGNAL_DROPPED = "signal_dropped"
    COMPLEX_FORMED = "complex_formed"
    QUORUM_TRIGGERED = "quorum_triggered"
    HOMEOSTASIS_INTERVENTION = "homeostasis_intervention"


@dataclass(slots=True)
class RuntimeEvent:
    """Structured event emitted during runtime execution."""

    event_id: str
    event_type: RuntimeEventType
    step: int
    node_id: str | None = None
    signal_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TopologySnapshot:
    """Execution-time view of node/channel/complex topology."""

    step: int
    node_ids: list[str]
    channel_names: list[str]
    active_complexes: list[str]
    receptor_index: dict[str, list[str]] = field(default_factory=dict)
    scope_index: dict[str, list[str]] = field(default_factory=dict)
    topology_index: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ReplayEventBundle:
    """Replay-oriented export containing events and topology timeline."""

    trace_id: str
    events: list[RuntimeEvent]
    topology_timeline: list[TopologySnapshot]
    checkpoint_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "events": [event.to_dict() for event in self.events],
            "topology_timeline": [snapshot.to_dict() for snapshot in self.topology_timeline],
            "checkpoint_ids": list(self.checkpoint_ids),
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class VisualizationGraph:
    """Future UI-friendly graph summary derived from runtime traces."""

    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    annotations: dict[str, Any] = field(default_factory=dict)
