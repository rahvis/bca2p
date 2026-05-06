"""Experimental MARL models for communication policy learning."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from bca2p.observability import TraceRecorder
from bca2p.observability.models import RuntimeEvent, RuntimeEventType


@dataclass(frozen=True, slots=True)
class CommunicationAction:
    """Single communication decision candidate in the training action space."""

    route_choice: str
    amplification_level: float = 1.0
    quorum_threshold: float = 0.5
    complex_members: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def action_key(self) -> str:
        members = ",".join(self.complex_members)
        return (
            f"route={self.route_choice}|amp={self.amplification_level:.2f}"
            f"|quorum={self.quorum_threshold:.2f}|complex={members}"
        )


@dataclass(slots=True)
class TrainingObservation:
    """Current centralized view of the environment used for policy updates."""

    agent_id: str
    state_key: str
    features: dict[str, float] = field(default_factory=dict)
    candidate_actions: list[CommunicationAction] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RewardBreakdown:
    """Reward components for centralized training and diagnostics."""

    task_reward: float = 0.0
    communication_cost: float = 0.0
    stability_penalty: float = 0.0
    failure_recovery_bonus: float = 0.0

    @property
    def total(self) -> float:
        return (
            self.task_reward
            - self.communication_cost
            - self.stability_penalty
            + self.failure_recovery_bonus
        )

    def to_dict(self) -> dict[str, float]:
        return {
            "task_reward": self.task_reward,
            "communication_cost": self.communication_cost,
            "stability_penalty": self.stability_penalty,
            "failure_recovery_bonus": self.failure_recovery_bonus,
            "total": self.total,
        }


@dataclass(slots=True)
class RolloutTransition:
    """One step of centralized training paired with decentralized action choice."""

    state_key: str
    action: CommunicationAction
    reward: RewardBreakdown
    next_state_key: str
    done: bool
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RolloutTrace:
    """Collected rollout information for learning and offline evaluation."""

    episode_id: str
    agent_id: str
    transitions: list[RolloutTransition] = field(default_factory=list)
    emitted_signals: int = 0
    delivered_signals: int = 0
    dropped_signals: int = 0
    homeostasis_interventions: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def total_reward(self) -> float:
        return sum(transition.reward.total for transition in self.transitions)

    @property
    def success(self) -> bool:
        return bool(self.metadata.get("success", False))


class TrainingEnvironment(Protocol):
    """Centralized training / decentralized execution environment contract."""

    def reset(self) -> TrainingObservation:
        """Start a new episode and return its first observation."""

    def step(
        self,
        action: CommunicationAction,
    ) -> tuple[TrainingObservation, RewardBreakdown, bool, dict[str, Any]]:
        """Advance one step using a decentralized communication action."""

    def baseline_action(self, observation: TrainingObservation) -> CommunicationAction:
        """Return a deterministic baseline action for comparison."""


@dataclass(slots=True)
class PolicyEvaluation:
    """Aggregate evaluation metrics for a policy on a benchmark environment."""

    average_reward: float
    success_rate: float
    episode_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LearnedCommunicationPolicy:
    """Simple value-table policy for communication decisions."""

    value_table: dict[str, dict[str, float]] = field(default_factory=dict)
    action_table: dict[str, dict[str, CommunicationAction]] = field(default_factory=dict)
    default_route: str = "fallback"
    metadata: dict[str, Any] = field(default_factory=dict)

    def score(self, state_key: str, action: CommunicationAction) -> float:
        return self.value_table.get(state_key, {}).get(action.action_key(), 0.0)

    def update(self, state_key: str, action: CommunicationAction, value: float) -> None:
        self.value_table.setdefault(state_key, {})[action.action_key()] = value
        self.action_table.setdefault(state_key, {})[action.action_key()] = action

    def select_action(
        self,
        observation: TrainingObservation,
        *,
        epsilon: float = 0.0,
        rng: random.Random | None = None,
    ) -> CommunicationAction:
        if not observation.candidate_actions:
            raise ValueError("candidate_actions must not be empty")
        chooser = rng or random.Random(0)
        if epsilon > 0.0 and chooser.random() < epsilon:
            return chooser.choice(observation.candidate_actions)
        ranked = sorted(
            observation.candidate_actions,
            key=lambda action: self.score(observation.state_key, action),
            reverse=True,
        )
        return ranked[0]

    def to_dict(self) -> dict[str, Any]:
        return {
            "value_table": self.value_table,
            "action_table": {
                state_key: {
                    action_key: {
                        "route_choice": action.route_choice,
                        "amplification_level": action.amplification_level,
                        "quorum_threshold": action.quorum_threshold,
                        "complex_members": list(action.complex_members),
                        "metadata": dict(action.metadata),
                    }
                    for action_key, action in actions.items()
                }
                for state_key, actions in self.action_table.items()
            },
            "default_route": self.default_route,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LearnedCommunicationPolicy":
        action_table: dict[str, dict[str, CommunicationAction]] = {}
        for state_key, actions in data.get("action_table", {}).items():
            action_table[state_key] = {}
            for action_key, action in actions.items():
                action_table[state_key][action_key] = CommunicationAction(
                    route_choice=action["route_choice"],
                    amplification_level=action["amplification_level"],
                    quorum_threshold=action["quorum_threshold"],
                    complex_members=tuple(action.get("complex_members", [])),
                    metadata=dict(action.get("metadata", {})),
                )
        return cls(
            value_table={
                state_key: {action_key: float(score) for action_key, score in actions.items()}
                for state_key, actions in data.get("value_table", {}).items()
            },
            action_table=action_table,
            default_route=data.get("default_route", "fallback"),
            metadata=dict(data.get("metadata", {})),
        )

    def export_json(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        return target

    @classmethod
    def from_json(cls, path: str | Path) -> "LearnedCommunicationPolicy":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(payload)


@dataclass(frozen=True, slots=True)
class TrainerConfig:
    """Configuration for centralized training."""

    episodes: int = 50
    learning_rate: float = 0.25
    discount: float = 0.9
    epsilon: float = 0.15
    seed: int = 7


@dataclass(slots=True)
class TrainingSummary:
    """End-to-end training result for a benchmark environment."""

    policy: LearnedCommunicationPolicy
    traces: list[RolloutTrace]
    evaluation: PolicyEvaluation
    baseline_evaluation: PolicyEvaluation
    metadata: dict[str, Any] = field(default_factory=dict)


class RolloutTraceCollector:
    """Transforms runtime traces into MARL-oriented rollout summaries."""

    def from_trace_recorder(
        self,
        recorder: TraceRecorder,
        *,
        episode_id: str,
        agent_id: str,
        transitions: list[RolloutTransition] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RolloutTrace:
        return self.from_runtime_events(
            recorder.events,
            episode_id=episode_id,
            agent_id=agent_id,
            transitions=transitions,
            metadata=metadata,
        )

    def from_runtime_events(
        self,
        events: list[RuntimeEvent],
        *,
        episode_id: str,
        agent_id: str,
        transitions: list[RolloutTransition] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RolloutTrace:
        emitted = self._count(events, RuntimeEventType.SIGNAL_EMITTED)
        delivered = self._count(events, RuntimeEventType.SIGNAL_DELIVERED)
        dropped = self._count(events, RuntimeEventType.SIGNAL_DROPPED)
        interventions = self._count(events, RuntimeEventType.HOMEOSTASIS_INTERVENTION)
        success = dropped == 0 and delivered >= emitted
        bundle = dict(metadata or {})
        bundle.setdefault("success", success)
        return RolloutTrace(
            episode_id=episode_id,
            agent_id=agent_id,
            transitions=list(transitions or []),
            emitted_signals=emitted,
            delivered_signals=delivered,
            dropped_signals=dropped,
            homeostasis_interventions=interventions,
            metadata=bundle,
        )

    @staticmethod
    def _count(events: list[RuntimeEvent], event_type: RuntimeEventType) -> int:
        return len([event for event in events if event.event_type == event_type])
