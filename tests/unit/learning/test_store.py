from __future__ import annotations

import pytest

from bca2p.core import (
    CausalFeedback,
    ContributionFactor,
    FeedbackType,
    SignalEnvelope,
    SignalMode,
    TopologyPolicy,
)
from bca2p.learning import (
    CausalDecisionNode,
    CausalGraphError,
    CausalGraphStore,
    CounterfactualError,
    CounterfactualType,
    DecisionType,
)


def make_signal(
    *,
    signal_id: str = "sig-1",
    parent_signal_id: str | None = None,
    amplification: float = 8.0,
    policy_tags: list[str] | None = None,
) -> SignalEnvelope:
    return SignalEnvelope(
        signal_id=signal_id,
        mode=SignalMode.PARACRINE,
        sender="planner",
        recipient_scope="research.team",
        receptor="research.query",
        payload={"query": "map patents"},
        causal_parent_id=parent_signal_id,
        amplification=amplification,
        confidence=0.85,
        policy_tags=policy_tags or ["complex:research_cluster"],
        trace_path=["planner"],
    )


def make_feedback(signal_id: str = "sig-1") -> CausalFeedback:
    return CausalFeedback(
        target_signal_id=signal_id,
        feedback_type=FeedbackType.OUTCOME,
        outcome="success",
        confidence=0.9,
        contributors=[
            ContributionFactor(source_id="planner", contribution=0.8, reason="correct routing"),
            ContributionFactor(source_id="critic", contribution=0.2, reason="quality gate"),
        ],
        counterfactuals={"if_signal_stayed_local": "worse"},
    )


def test_causal_graph_store_records_signals_and_feedback() -> None:
    store = CausalGraphStore()
    edge = store.record_signal(make_signal(), step=1)
    outcome = store.ingest_feedback(make_feedback(), step=2)

    assert edge.signal_id == "sig-1"
    assert outcome.target_signal_id == "sig-1"
    assert store.get_feedback("sig-1")[0].outcome == "success"


def test_causal_chain_returns_root_to_leaf_order() -> None:
    store = CausalGraphStore()
    store.record_signal(make_signal(signal_id="root"), step=0)
    store.record_signal(make_signal(signal_id="child", parent_signal_id="root"), step=1)
    chain = store.causal_chain("child")
    assert [edge.signal_id for edge in chain] == ["root", "child"]


def test_record_decision_and_retrieve_signal_summary() -> None:
    store = CausalGraphStore()
    store.record_signal(make_signal(), step=1)
    store.record_decision(
        CausalDecisionNode(
            decision_id="decision-1",
            node_id="planner",
            decision_type=DecisionType.ROUTING,
            value="researcher",
            confidence=0.8,
            related_signal_id="sig-1",
        )
    )
    store.ingest_feedback(make_feedback(), step=2)

    summary = store.summarize_contributions("sig-1")
    assert summary.target_signal_id == "sig-1"
    assert summary.sender_contribution > 0
    assert summary.receptor_match_quality == 1.0
    assert summary.complex_contribution > 0.5


def test_ingesting_feedback_for_unknown_signal_raises() -> None:
    store = CausalGraphStore()
    with pytest.raises(CausalGraphError):
        store.ingest_feedback(make_feedback("missing"))


def test_counterfactual_queries_cover_supported_cases() -> None:
    store = CausalGraphStore()
    store.record_signal(make_signal(), step=1)
    store.ingest_feedback(make_feedback(), step=2)

    local = store.what_if_signal_stayed_local("sig-1")
    assert local.query_type == CounterfactualType.SIGNAL_STAYED_LOCAL

    absent = store.what_if_complex_member_absent("sig-1", member_id="planner")
    assert absent.query_type == CounterfactualType.COMPLEX_MEMBER_ABSENT

    lower = store.what_if_amplification_lower("sig-1", new_amplification=2.0)
    assert lower.query_type == CounterfactualType.AMPLIFICATION_LOWER


def test_invalid_counterfactual_amplification_raises() -> None:
    store = CausalGraphStore()
    store.record_signal(make_signal(), step=1)
    with pytest.raises(CounterfactualError):
        store.what_if_amplification_lower("sig-1", new_amplification=-1.0)


def test_safe_topology_refinement_can_apply_when_confident() -> None:
    store = CausalGraphStore()
    store.record_signal(make_signal(), step=1)
    store.ingest_feedback(make_feedback(), step=2)
    policy = TopologyPolicy(policy_id="balanced")

    proposal = store.suggest_topology_refinement(policy, signal_id="sig-1", min_confidence=0.6)
    assert proposal.safe_to_apply is True
    assert proposal.recommended_value.policy_id == "balanced"
    assert proposal.recommended_value.affinity_weight >= policy.affinity_weight


def test_refinements_fall_back_when_confidence_is_too_low() -> None:
    store = CausalGraphStore()
    store.record_signal(make_signal(signal_id="sig-2"), step=1)
    low_confidence_feedback = CausalFeedback(
        target_signal_id="sig-2",
        feedback_type=FeedbackType.OUTCOME,
        outcome="uncertain",
        confidence=0.2,
    )
    store.ingest_feedback(low_confidence_feedback, step=2)

    topology_proposal = store.suggest_topology_refinement(
        TopologyPolicy(policy_id="balanced"),
        signal_id="sig-2",
        min_confidence=0.6,
    )
    amplification_proposal = store.suggest_amplification_refinement(
        signal_id="sig-2",
        current_amplification=4.0,
        max_cap=80.0,
        min_confidence=0.6,
    )
    complex_proposal = store.suggest_complex_membership_refinement(
        signal_id="sig-2",
        member_id="planner",
        min_confidence=0.6,
    )

    assert topology_proposal.safe_to_apply is False
    assert amplification_proposal.safe_to_apply is False
    assert amplification_proposal.recommended_value == 4.0
    assert complex_proposal.recommended_value == "retain"


def test_deterministic_fallback_routing_returns_default_without_safe_proposals() -> None:
    store = CausalGraphStore()
    store.record_signal(make_signal(signal_id="sig-3"), step=1)
    store.ingest_feedback(make_feedback("sig-3"), step=2)
    policy = TopologyPolicy(policy_id="balanced")
    proposal = store.suggest_topology_refinement(policy, signal_id="sig-3")

    fallback = store.fallback_routing_choice([proposal], fallback_target="default-agent")
    assert fallback == "balanced"

    fallback_empty = store.fallback_routing_choice([], fallback_target="default-agent")
    assert fallback_empty == "default-agent"
