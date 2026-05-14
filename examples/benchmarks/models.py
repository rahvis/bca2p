"""Shared dataclasses for the bca2p coordination benchmark."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ApproachName = Literal["baseline", "bca2p"]


@dataclass(frozen=True)
class CoordinationMeasurements:
    """Raw deterministic measurements collected for an approach run."""

    correct_decision: bool
    should_escalate: bool
    escalated: bool
    total_messages: int
    relevant_deliveries: int
    irrelevant_deliveries: int
    duplicate_work_units: int
    context_tokens: int
    latency_ms: int
    escalation_delay_steps: int
    false_escalations: int
    missed_escalations: int
    retry_storms: int
    route_flaps: int
    amplification_events: int
    replay_artifacts: int
    evidence_artifacts: int
    causal_links: int
    feedback_records: int
    quorum_observed: bool = False


@dataclass(frozen=True)
class ScenarioSpec:
    """Benchmark scenario definition shared by baseline and bca2p runners."""

    slug: str
    use_case: str
    dataset: str
    dataset_url: str
    dataset_reason: str
    ground_truth: str
    scope: str
    agent_roles: tuple[str, ...]
    signal_modes: tuple[str, ...]
    receptors: tuple[str, ...]
    stressors: tuple[str, ...]
    baseline: CoordinationMeasurements
    bca2p: CoordinationMeasurements
    message_ceiling: int = 64
    token_ceiling: int = 64_000
    latency_ceiling_ms: int = 30_000
    deadline_steps: int = 6
    stability_ceiling: int = 8


@dataclass(frozen=True)
class ApproachResult:
    """Scored result for one approach within a scenario."""

    approach: ApproachName
    score: float
    metrics: dict[str, float]
    measurements: CoordinationMeasurements
    trace: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScenarioComparison:
    """Baseline versus bca2p comparison for one scenario."""

    scenario: ScenarioSpec
    baseline: ApproachResult
    bca2p: ApproachResult

    @property
    def score_delta(self) -> float:
        return round(self.bca2p.score - self.baseline.score, 2)


@dataclass(frozen=True)
class LeaderboardEntry:
    """Public leaderboard row derived from a scenario comparison."""

    rank: int
    scenario_slug: str
    use_case: str
    dataset: str
    baseline_score: float
    bca2p_score: float
    score_delta: float
    winning_claim: str
