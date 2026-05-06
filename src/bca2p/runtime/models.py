"""Dataclasses and configuration models for runtime execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from bca2p.core import SignalEnvelope
from bca2p.graph import ComplexLifecycleState


@dataclass(frozen=True)
class RuntimeConfig:
    """Runtime limits and execution controls."""

    max_steps: int = 50
    step_timeout_seconds: float | None = None
    max_retries: int = 0
    retry_backoff_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.max_steps < 1:
            raise ValueError("max_steps must be at least 1")
        if self.step_timeout_seconds is not None and self.step_timeout_seconds <= 0:
            raise ValueError("step_timeout_seconds must be positive when provided")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.retry_backoff_seconds < 0:
            raise ValueError("retry_backoff_seconds must be non-negative")


@dataclass
class StateSnapshot:
    """Checkpointed snapshot of runtime state after a super-step."""

    snapshot_id: str
    step: int
    state: Any
    channel_values: dict[str, Any]
    pending_signals: list[SignalEnvelope] = field(default_factory=list)
    active_nodes: list[str] = field(default_factory=list)
    updated_channels: list[str] = field(default_factory=list)
    complex_states: dict[str, ComplexLifecycleState] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RuntimeResult:
    """Final result from a runtime invocation."""

    final_state: Any
    final_snapshot: StateSnapshot | None
    steps_executed: int
    completed: bool
