"""Node contracts and signal emission helpers for the graph layer."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from typing import Any, Awaitable, Callable, TypeAlias

from bca2p.core import (
    ArtifactRef,
    PriorityLevel,
    ReceptorSpec,
    SignalEnvelope,
    SignalMode,
    TrustLevel,
)


BioNodeHandler: TypeAlias = Callable[..., Any]


@dataclass
class SignalEmitter:
    """Helper used by node handlers to stage outgoing typed signals."""

    sender: str
    emitted_signals: list[SignalEnvelope] = field(default_factory=list)

    def emit(
        self,
        *,
        mode: SignalMode,
        recipient_scope: str,
        payload: dict[str, Any] | None = None,
        receptor: str | None = None,
        signal_id: str | None = None,
        priority: PriorityLevel = PriorityLevel.MEDIUM,
        ttl: float | None = None,
        decay: float | None = None,
        amplification: float = 1.0,
        confidence: float | None = None,
        causal_parent_id: str | None = None,
        correlation_id: str | None = None,
        trace_path: list[str] | None = None,
        trust_level: TrustLevel | None = None,
        policy_tags: list[str] | None = None,
        artifact_refs: list[ArtifactRef] | None = None,
    ) -> SignalEnvelope:
        signal = SignalEnvelope(
            signal_id=signal_id or f"{self.sender}:{len(self.emitted_signals) + 1}",
            mode=mode,
            sender=self.sender,
            recipient_scope=recipient_scope,
            receptor=receptor,
            payload=payload or {},
            priority=priority,
            ttl=ttl,
            decay=decay,
            amplification=amplification,
            confidence=confidence,
            causal_parent_id=causal_parent_id,
            correlation_id=correlation_id,
            trace_path=trace_path or [self.sender],
            trust_level=trust_level,
            policy_tags=policy_tags or [],
            artifact_refs=artifact_refs or [],
        )
        self.emitted_signals.append(signal)
        return signal


@dataclass(frozen=True)
class BioNodeContext:
    """Context object provided to node handlers."""

    node_id: str
    emitter: SignalEmitter
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BioNode:
    """Graph-local node declaration for a bio-inspired agent handler."""

    node_id: str
    handler: BioNodeHandler
    receptors: list[ReceptorSpec] = field(default_factory=list)
    scope_subscriptions: list[str] = field(default_factory=list)
    topology_subscriptions: list[str] = field(default_factory=list)
    input_channels: list[str] = field(default_factory=list)
    output_channel: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise ValueError("node_id must not be empty")
        if not callable(self.handler):
            raise TypeError("handler must be callable")

    @property
    def is_async(self) -> bool:
        return inspect.iscoroutinefunction(self.handler)

    def create_context(self) -> BioNodeContext:
        return BioNodeContext(node_id=self.node_id, emitter=SignalEmitter(sender=self.node_id))

    def receptor_ids(self) -> list[str]:
        return [receptor.receptor_id for receptor in self.receptors]

    def matches_signal(self, signal: SignalEnvelope) -> bool:
        if signal.receptor and signal.receptor in self.receptor_ids():
            return True

        if any(fnmatchcase(signal.recipient_scope, pattern) for pattern in self.scope_subscriptions):
            return True

        if self.topology_subscriptions:
            signal_tags = set(signal.policy_tags)
            if signal_tags.intersection(self.topology_subscriptions):
                return True

        return False

    def invoke(self, state: Any, *, context: BioNodeContext | None = None) -> Any | Awaitable[Any]:
        runtime_context = context or self.create_context()
        return self.handler(state, runtime_context)
