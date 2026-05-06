"""Typed causal entities and refinement proposals for bca2p."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from bca2p.core import FeedbackType, SignalMode


class DecisionType(StrEnum):
    """Decision classes tracked in the causal graph."""

    ROUTING = "routing"
    AMPLIFICATION = "amplification"
    COMPLEX_MEMBERSHIP = "complex_membership"
    QUORUM = "quorum"


class CounterfactualType(StrEnum):
    """Supported counterfactual query families."""

    SIGNAL_STAYED_LOCAL = "signal_stayed_local"
    COMPLEX_MEMBER_ABSENT = "complex_member_absent"
    AMPLIFICATION_LOWER = "amplification_lower"


@dataclass(slots=True)
class CausalSignalEdge:
    """A recorded signal transition inside the causal graph."""

    signal_id: str
    sender: str
    recipient_scope: str
    mode: SignalMode
    receptor: str | None = None
    parent_signal_id: str | None = None
    step: int | None = None
    amplification: float = 1.0
    confidence: float | None = None
    policy_tags: list[str] = field(default_factory=list)
    payload_keys: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CausalDecisionNode:
    """A recorded runtime decision affecting communication behavior."""

    decision_id: str
    node_id: str
    decision_type: DecisionType
    value: Any
    confidence: float | None = None
    step: int | None = None
    related_signal_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CausalOutcomeNode:
    """A recorded outcome emitted through structured causal feedback."""

    outcome_id: str
    target_signal_id: str
    feedback_type: FeedbackType
    outcome: str
    confidence: float | None = None
    step: int | None = None
    contributor_scores: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ContributionSummary:
    """Aggregated contribution heuristics for a target signal."""

    target_signal_id: str
    sender_contribution: float
    receptor_match_quality: float
    topology_contribution: float
    complex_contribution: float
    confidence: float
    reasons: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CounterfactualResult:
    """Structured answer to a causal what-if query."""

    query_type: CounterfactualType
    target_signal_id: str
    estimated_outcome_delta: float
    confidence: float
    explanation: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class PolicyRefinementProposal:
    """Safe policy update suggestion derived from causal feedback."""

    proposal_id: str
    target: str
    update_type: DecisionType
    recommended_value: Any
    confidence: float
    reason: str
    safe_to_apply: bool
    metadata: dict[str, Any] = field(default_factory=dict)
