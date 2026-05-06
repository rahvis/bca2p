"""Enum definitions for the bca2p core protocol layer."""

from __future__ import annotations

from enum import StrEnum


class SignalMode(StrEnum):
    """Communication modes derived from biological signaling patterns."""

    AUTOCRINE = "autocrine"
    PARACRINE = "paracrine"
    ENDOCRINE = "endocrine"
    JUXTACRINE = "juxtacrine"
    SYNAPTIC = "synaptic"
    VESICLE = "vesicle"
    QUORUM = "quorum"


class PriorityLevel(StrEnum):
    """Delivery priority hints for signal routing."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TrustLevel(StrEnum):
    """Trust levels used to gate sensitive receptors and routes."""

    UNTRUSTED = "untrusted"
    INTERNAL = "internal"
    TRUSTED = "trusted"
    VERIFIED = "verified"


class FeedbackType(StrEnum):
    """Structured feedback categories for causal learning."""

    OUTCOME = "outcome"
    REWARD = "reward"
    BLAME = "blame"
    DAMPING = "damping"
    ESCALATION = "escalation"


class TopologyStrategy(StrEnum):
    """Topology adaptation strategies."""

    STATIC = "static"
    AFFINITY_WEIGHTED = "affinity_weighted"
    URGENCY_WEIGHTED = "urgency_weighted"
    HISTORY_WEIGHTED = "history_weighted"
    BALANCED = "balanced"
