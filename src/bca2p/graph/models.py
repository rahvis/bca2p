"""Compiled graph and lifecycle models for the graph layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from bca2p.core import ComplexSpec, HomeostasisPolicy, QuorumRule

from .channels import BaseChannel
from .nodes import BioNode


class ComplexLifecycleState(StrEnum):
    """Lifecycle states for temporary coordination complexes."""

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    ABORTED = "aborted"


@dataclass
class CompiledComplex:
    """Runtime-ready complex declaration with mutable lifecycle state."""

    spec: ComplexSpec
    state: ComplexLifecycleState = ComplexLifecycleState.PENDING

    @property
    def scaffold_id(self) -> str:
        return self.spec.scaffold_id


@dataclass
class CompiledBioGraph:
    """Frozen graph definition returned by ``BioGraph.compile()``."""

    nodes: dict[str, BioNode]
    channels: dict[str, BaseChannel]
    complexes: dict[str, CompiledComplex]
    quorum_rules: dict[str, QuorumRule]
    homeostasis_policy: HomeostasisPolicy | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_node(self, node_id: str) -> BioNode:
        return self.nodes[node_id]

    def get_channel(self, channel_name: str) -> BaseChannel:
        return self.channels[channel_name]

    def get_complex_state(self, scaffold_id: str) -> ComplexLifecycleState:
        return self.complexes[scaffold_id].state

    def set_complex_state(
        self,
        scaffold_id: str,
        state: ComplexLifecycleState,
    ) -> None:
        self.complexes[scaffold_id].state = state

    def matching_nodes_for_signal(self, signal: Any) -> list[BioNode]:
        return [node for node in self.nodes.values() if node.matches_signal(signal)]
