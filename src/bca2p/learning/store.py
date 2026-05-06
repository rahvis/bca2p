"""Causal graph store, feedback ingestion, and policy refinement heuristics."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from typing import Any

from bca2p.core import CausalFeedback, ContributionFactor, SignalEnvelope, TopologyPolicy

from .exceptions import CausalGraphError, CounterfactualError
from .models import (
    CausalDecisionNode,
    CausalOutcomeNode,
    CausalSignalEdge,
    ContributionSummary,
    CounterfactualResult,
    CounterfactualType,
    DecisionType,
    PolicyRefinementProposal,
)


class CausalGraphStore:
    """Stores causal traces, feedback, and safe refinement recommendations."""

    def __init__(self) -> None:
        self._signals: dict[str, CausalSignalEdge] = {}
        self._decisions: dict[str, CausalDecisionNode] = {}
        self._outcomes: dict[str, list[CausalOutcomeNode]] = defaultdict(list)
        self._children_by_signal: dict[str, list[str]] = defaultdict(list)

    def record_signal(self, signal: SignalEnvelope, *, step: int | None = None) -> CausalSignalEdge:
        edge = CausalSignalEdge(
            signal_id=signal.signal_id,
            sender=signal.sender,
            recipient_scope=signal.recipient_scope,
            mode=signal.mode,
            receptor=signal.receptor,
            parent_signal_id=signal.causal_parent_id,
            step=step,
            amplification=signal.amplification,
            confidence=signal.confidence,
            policy_tags=list(signal.policy_tags),
            payload_keys=sorted(signal.payload.keys()),
        )
        self._signals[edge.signal_id] = edge
        if edge.parent_signal_id is not None:
            self._children_by_signal[edge.parent_signal_id].append(edge.signal_id)
        return edge

    def record_decision(
        self,
        decision: CausalDecisionNode,
    ) -> CausalDecisionNode:
        self._decisions[decision.decision_id] = decision
        return decision

    def ingest_feedback(
        self,
        feedback: CausalFeedback,
        *,
        step: int | None = None,
    ) -> CausalOutcomeNode:
        if feedback.target_signal_id not in self._signals:
            raise CausalGraphError(
                f"Cannot ingest feedback for unknown signal {feedback.target_signal_id!r}",
            )

        contributor_scores = self._normalize_contributors(feedback.contributors)
        outcome = CausalOutcomeNode(
            outcome_id=f"outcome:{feedback.target_signal_id}:{len(self._outcomes[feedback.target_signal_id]) + 1}",
            target_signal_id=feedback.target_signal_id,
            feedback_type=feedback.feedback_type,
            outcome=feedback.outcome,
            confidence=feedback.confidence,
            step=step,
            contributor_scores=contributor_scores,
            metadata={
                "counterfactuals": deepcopy(feedback.counterfactuals),
                **deepcopy(feedback.metadata),
            },
        )
        self._outcomes[feedback.target_signal_id].append(outcome)
        return outcome

    def get_signal(self, signal_id: str) -> CausalSignalEdge:
        try:
            return self._signals[signal_id]
        except KeyError as exc:
            raise CausalGraphError(f"Unknown signal {signal_id!r}") from exc

    def get_feedback(self, signal_id: str) -> list[CausalOutcomeNode]:
        return list(self._outcomes.get(signal_id, []))

    def causal_chain(self, signal_id: str) -> list[CausalSignalEdge]:
        chain: list[CausalSignalEdge] = []
        current = self.get_signal(signal_id)
        while True:
            chain.append(current)
            if current.parent_signal_id is None:
                break
            current = self.get_signal(current.parent_signal_id)
        chain.reverse()
        return chain

    def summarize_contributions(self, signal_id: str) -> ContributionSummary:
        signal = self.get_signal(signal_id)
        outcomes = self.get_feedback(signal_id)

        sender_contribution = self._average_for_source(outcomes, signal.sender)
        receptor_match_quality = 1.0 if signal.receptor else 0.5
        topology_contribution = min(1.0, 0.2 + (0.15 * len(signal.policy_tags)))
        complex_contribution = 0.85 if any(tag.startswith("complex:") for tag in signal.policy_tags) else 0.35

        confidence_values = [outcome.confidence for outcome in outcomes if outcome.confidence is not None]
        confidence = (
            sum(confidence_values) / len(confidence_values)
            if confidence_values
            else signal.confidence if signal.confidence is not None else 0.5
        )

        reasons = [
            f"sender contribution estimated from {len(outcomes)} outcomes",
            "receptor quality boosted for explicit receptor binding" if signal.receptor else "no explicit receptor binding present",
            f"topology contribution derived from {len(signal.policy_tags)} policy tags",
            "complex contribution increased due to complex-tagged route"
            if any(tag.startswith("complex:") for tag in signal.policy_tags)
            else "no complex-specific routing evidence present",
        ]

        return ContributionSummary(
            target_signal_id=signal_id,
            sender_contribution=sender_contribution,
            receptor_match_quality=receptor_match_quality,
            topology_contribution=topology_contribution,
            complex_contribution=complex_contribution,
            confidence=confidence,
            reasons=reasons,
        )

    def what_if_signal_stayed_local(self, signal_id: str) -> CounterfactualResult:
        signal = self.get_signal(signal_id)
        summary = self.summarize_contributions(signal_id)
        delta = -0.2 if signal.mode.value in {"endocrine", "synaptic"} else -0.05
        return CounterfactualResult(
            query_type=CounterfactualType.SIGNAL_STAYED_LOCAL,
            target_signal_id=signal_id,
            estimated_outcome_delta=delta,
            confidence=summary.confidence,
            explanation=(
                "Estimated outcome would decrease if the signal stayed local because "
                f"the original mode was {signal.mode.value!r} and wider dissemination was likely useful."
            ),
            metadata={"original_mode": signal.mode.value},
        )

    def what_if_complex_member_absent(
        self,
        signal_id: str,
        *,
        member_id: str,
    ) -> CounterfactualResult:
        signal = self.get_signal(signal_id)
        summary = self.summarize_contributions(signal_id)
        supporting_outcomes = self.get_feedback(signal_id)
        explicit_member_score = [
            outcome.contributor_scores.get(member_id)
            for outcome in supporting_outcomes
            if member_id in outcome.contributor_scores
        ]
        delta = -(sum(explicit_member_score) / len(explicit_member_score)) if explicit_member_score else -0.1
        return CounterfactualResult(
            query_type=CounterfactualType.COMPLEX_MEMBER_ABSENT,
            target_signal_id=signal_id,
            estimated_outcome_delta=delta,
            confidence=summary.confidence,
            explanation=(
                f"Estimated outcome delta reflects the absence of complex member {member_id!r} "
                "based on recorded contributor scores."
            ),
            metadata={"member_id": member_id, "policy_tags": list(signal.policy_tags)},
        )

    def what_if_amplification_lower(
        self,
        signal_id: str,
        *,
        new_amplification: float,
    ) -> CounterfactualResult:
        signal = self.get_signal(signal_id)
        if new_amplification < 0:
            raise CounterfactualError("new_amplification must be non-negative")
        summary = self.summarize_contributions(signal_id)
        if signal.amplification <= 0:
            delta = 0.0
        else:
            ratio = max(0.0, min(1.0, new_amplification / signal.amplification))
            delta = ratio - 1.0
        return CounterfactualResult(
            query_type=CounterfactualType.AMPLIFICATION_LOWER,
            target_signal_id=signal_id,
            estimated_outcome_delta=delta,
            confidence=summary.confidence,
            explanation=(
                "Estimated outcome delta is based on the proportional reduction in amplification "
                f"from {signal.amplification} to {new_amplification}."
            ),
            metadata={"original_amplification": signal.amplification, "new_amplification": new_amplification},
        )

    def suggest_topology_refinement(
        self,
        topology_policy: TopologyPolicy,
        *,
        signal_id: str,
        min_confidence: float = 0.6,
    ) -> PolicyRefinementProposal:
        summary = self.summarize_contributions(signal_id)
        safe_to_apply = summary.confidence >= min_confidence
        if safe_to_apply:
            recommended = topology_policy.model_copy(
                update={
                    "affinity_weight": round(
                        topology_policy.affinity_weight + (summary.receptor_match_quality * 0.1),
                        3,
                    ),
                    "history_weight": round(
                        topology_policy.history_weight + (summary.sender_contribution * 0.1),
                        3,
                    ),
                }
            )
            reason = "Increase affinity/history weighting in response to strong structured signaling outcomes"
        else:
            recommended = topology_policy
            reason = "Confidence below threshold; retain deterministic fallback topology weights"
        return PolicyRefinementProposal(
            proposal_id=f"proposal:topology:{signal_id}",
            target=topology_policy.policy_id,
            update_type=DecisionType.ROUTING,
            recommended_value=recommended,
            confidence=summary.confidence,
            reason=reason,
            safe_to_apply=safe_to_apply,
            metadata={"signal_id": signal_id},
        )

    def suggest_amplification_refinement(
        self,
        *,
        signal_id: str,
        current_amplification: float,
        max_cap: float,
        min_confidence: float = 0.6,
    ) -> PolicyRefinementProposal:
        summary = self.summarize_contributions(signal_id)
        safe_to_apply = summary.confidence >= min_confidence
        if safe_to_apply:
            recommended = min(max_cap, round(current_amplification + (summary.topology_contribution * 5.0), 3))
            reason = "Increase amplification slightly because routed signal showed positive topology contribution"
        else:
            recommended = current_amplification
            reason = "Confidence below threshold; keep deterministic fallback amplification"
        return PolicyRefinementProposal(
            proposal_id=f"proposal:amplification:{signal_id}",
            target=signal_id,
            update_type=DecisionType.AMPLIFICATION,
            recommended_value=recommended,
            confidence=summary.confidence,
            reason=reason,
            safe_to_apply=safe_to_apply,
            metadata={"signal_id": signal_id, "max_cap": max_cap},
        )

    def suggest_complex_membership_refinement(
        self,
        *,
        signal_id: str,
        member_id: str,
        min_confidence: float = 0.6,
    ) -> PolicyRefinementProposal:
        summary = self.summarize_contributions(signal_id)
        counterfactual = self.what_if_complex_member_absent(signal_id, member_id=member_id)
        safe_to_apply = summary.confidence >= min_confidence
        recommended = "retain" if counterfactual.estimated_outcome_delta < 0 else "remove"
        if not safe_to_apply:
            recommended = "retain"
        reason = (
            f"Complex member {member_id!r} appears beneficial"
            if recommended == "retain"
            else f"Complex member {member_id!r} appears non-essential"
        )
        if not safe_to_apply:
            reason = "Confidence below threshold; retain deterministic complex membership"
        return PolicyRefinementProposal(
            proposal_id=f"proposal:complex:{signal_id}:{member_id}",
            target=member_id,
            update_type=DecisionType.COMPLEX_MEMBERSHIP,
            recommended_value=recommended,
            confidence=summary.confidence,
            reason=reason,
            safe_to_apply=safe_to_apply,
            metadata={"signal_id": signal_id},
        )

    def fallback_routing_choice(
        self,
        proposals: list[PolicyRefinementProposal],
        *,
        fallback_target: str,
        min_confidence: float = 0.6,
    ) -> str:
        applicable = [
            proposal
            for proposal in proposals
            if proposal.update_type == DecisionType.ROUTING and proposal.safe_to_apply
            and proposal.confidence >= min_confidence
        ]
        if not applicable:
            return fallback_target
        return applicable[0].target

    def _average_for_source(self, outcomes: list[CausalOutcomeNode], source_id: str) -> float:
        scores = [
            outcome.contributor_scores[source_id]
            for outcome in outcomes
            if source_id in outcome.contributor_scores
        ]
        if not scores:
            return 0.5
        average = sum(scores) / len(scores)
        return max(0.0, min(1.0, average))

    def _normalize_contributors(self, contributors: list[ContributionFactor]) -> dict[str, float]:
        if not contributors:
            return {}

        result: dict[str, float] = {}
        for contributor in contributors:
            result[contributor.source_id] = contributor.contribution
        return result
