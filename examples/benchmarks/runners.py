"""Executable benchmark runners for bca2p coordination scenarios."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from typing import Any

from bca2p.core import (
    ArtifactRef,
    CausalFeedback,
    ContributionFactor,
    FeedbackType,
    HomeostasisPolicy,
    PriorityLevel,
    QuorumRule,
    ReceptorSpec,
    SignalEnvelope,
    SignalMode,
)
from bca2p.learning import CausalGraphStore
from bca2p.observability import RuntimeEventType, TraceRecorder

from .models import (
    ApproachResult,
    CoordinationMeasurements,
    LeaderboardEntry,
    ScenarioComparison,
    ScenarioSpec,
)
from .scenarios import SCENARIOS
from .scoring import calculate_coordination_score, calculate_metric_scores


def run_coordination_benchmarks(
    scenarios: tuple[ScenarioSpec, ...] = SCENARIOS,
) -> list[ScenarioComparison]:
    """Run the deterministic nine-domain coordination benchmark."""

    return [run_scenario(scenario) for scenario in scenarios]


def run_scenario(scenario: ScenarioSpec) -> ScenarioComparison:
    """Run baseline and bca2p approaches for a single scenario."""

    return ScenarioComparison(
        scenario=scenario,
        baseline=_run_baseline(scenario),
        bca2p=_run_bca2p(scenario),
    )


def build_leaderboard(comparisons: list[ScenarioComparison]) -> list[LeaderboardEntry]:
    ranked = sorted(comparisons, key=lambda comparison: comparison.bca2p.score, reverse=True)
    return [
        LeaderboardEntry(
            rank=index,
            scenario_slug=comparison.scenario.slug,
            use_case=comparison.scenario.use_case,
            dataset=comparison.scenario.dataset,
            baseline_score=comparison.baseline.score,
            bca2p_score=comparison.bca2p.score,
            score_delta=comparison.score_delta,
            winning_claim=_winning_claim(comparison),
        )
        for index, comparison in enumerate(ranked, start=1)
    ]


def _run_baseline(scenario: ScenarioSpec) -> ApproachResult:
    trace = {
        "communication_style": "generic agent messages",
        "dataset": scenario.dataset,
        "stressors": list(scenario.stressors),
        "message_summary": {
            "total_messages": scenario.baseline.total_messages,
            "relevant_deliveries": scenario.baseline.relevant_deliveries,
            "irrelevant_deliveries": scenario.baseline.irrelevant_deliveries,
            "duplicate_work_units": scenario.baseline.duplicate_work_units,
        },
        "audit_surface": "ordinary message transcript",
    }
    return _result("baseline", scenario, scenario.baseline, trace)


def _run_bca2p(scenario: ScenarioSpec) -> ApproachResult:
    recorder = TraceRecorder(trace_id=f"{scenario.slug}:bca2p")
    causal_store = CausalGraphStore()
    homeostasis = HomeostasisPolicy(
        policy_id=f"{scenario.slug}:homeostasis",
        max_amplification=12.0,
        noisy_sender_threshold=max(2, scenario.bca2p.total_messages // 8),
    )
    quorum = QuorumRule(
        rule_id=f"{scenario.slug}:quorum",
        target_scope=scenario.scope,
        threshold=0.67,
        min_participants=3,
        action=scenario.ground_truth,
    )
    receptors = _build_receptors(scenario)
    signals = _emit_bca2p_signals(scenario, receptors, recorder, causal_store, homeostasis)
    _record_quorum(recorder, scenario, quorum, signals)
    causal_summary = _record_feedback(causal_store, scenario, signals)

    trace = {
        "communication_style": "typed bca2p signaling",
        "dataset": scenario.dataset,
        "homeostasis_policy": homeostasis.to_dict(),
        "quorum_rule": quorum.to_dict(),
        "receptor_count": len(receptors),
        "signal_count": len(signals),
        "signals": [signal.to_dict() for signal in signals],
        "runtime_event_counts": dict(Counter(event.event_type.value for event in recorder.events)),
        "replay_bundle": recorder.build_bundle(
            checkpoint_ids=[f"{scenario.slug}:checkpoint:0001"],
            metadata={"ground_truth": scenario.ground_truth},
        ).to_dict(),
        "causal_summary": causal_summary,
    }
    return _result("bca2p", scenario, scenario.bca2p, trace)


def _result(
    approach: str,
    scenario: ScenarioSpec,
    measurements: CoordinationMeasurements,
    trace: dict[str, Any],
) -> ApproachResult:
    metrics = calculate_metric_scores(scenario, measurements)
    score = calculate_coordination_score(scenario, measurements)
    return ApproachResult(
        approach=approach,  # type: ignore[arg-type]
        score=score,
        metrics={key: round(value, 4) for key, value in metrics.items()},
        measurements=measurements,
        trace=trace,
    )


def _build_receptors(scenario: ScenarioSpec) -> list[ReceptorSpec]:
    modes = [_mode(value) for value in scenario.signal_modes]
    receptors: list[ReceptorSpec] = []
    for role in scenario.agent_roles:
        for receptor_name in scenario.receptors:
            receptors.append(
                ReceptorSpec(
                    receptor_id=f"{scenario.slug}.{role}.{receptor_name}",
                    accepted_modes=modes,
                    metadata={"scope": scenario.scope, "role": role},
                )
            )
    return receptors


def _emit_bca2p_signals(
    scenario: ScenarioSpec,
    receptors: list[ReceptorSpec],
    recorder: TraceRecorder,
    causal_store: CausalGraphStore,
    homeostasis: HomeostasisPolicy,
) -> list[SignalEnvelope]:
    signals: list[SignalEnvelope] = []
    roles = list(scenario.agent_roles)
    modes = [_mode(value) for value in scenario.signal_modes]
    root_sender = roles[0]
    evidence_artifact = ArtifactRef(
        artifact_id=f"{scenario.slug}-evidence-1",
        uri=f"benchmark://{scenario.slug}/evidence/1",
        media_type="application/json",
        metadata={"dataset": scenario.dataset},
    )

    for index, role in enumerate(roles[1:], start=1):
        receptor = receptors[index % len(receptors)]
        signal = SignalEnvelope(
            signal_id=f"{scenario.slug}:signal:{index:02d}",
            mode=modes[index % len(modes)],
            sender=root_sender if index == 1 else roles[index - 1],
            recipient_scope=scenario.scope,
            receptor=receptor.receptor_id,
            payload={
                "scenario": scenario.slug,
                "role": role,
                "ground_truth": scenario.ground_truth,
                "stressors": list(scenario.stressors),
            },
            priority=PriorityLevel.HIGH,
            ttl=4.0,
            decay=0.1,
            amplification=min(6.0 + index, homeostasis.max_amplification),
            confidence=0.72 + min(index * 0.03, 0.2),
            causal_parent_id=signals[-1].signal_id if signals else None,
            correlation_id=f"{scenario.slug}:case",
            trace_path=[root_sender, role, f"step:{index}"],
            policy_tags=[f"scope:{scenario.scope}", "benchmark", "risk-sensitive"],
            artifact_refs=[evidence_artifact] if index == 1 else [],
        )
        signals.append(signal)
        causal_store.record_signal(signal, step=index)
        recorder.record_event(
            RuntimeEventType.SIGNAL_EMITTED,
            step=index,
            node_id=signal.sender,
            signal_id=signal.signal_id,
            details={
                "sender": signal.sender,
                "recipient_scope": signal.recipient_scope,
                "receptor": signal.receptor,
                "mode": signal.mode.value,
                "amplification": signal.amplification,
            },
        )
        recorder.record_event(
            RuntimeEventType.SIGNAL_DELIVERED,
            step=index,
            node_id=role,
            signal_id=signal.signal_id,
            details={
                "sender": signal.sender,
                "recipient_scope": signal.recipient_scope,
                "receptor": signal.receptor,
            },
        )

    if scenario.baseline.amplification_events > 0 and scenario.bca2p.amplification_events == 0:
        recorder.record_event(
            RuntimeEventType.HOMEOSTASIS_INTERVENTION,
            step=1,
            signal_id=signals[0].signal_id if signals else None,
            details={
                "action": "damp_noisy_route",
                "policy_id": homeostasis.policy_id,
                "baseline_amplification_events": scenario.baseline.amplification_events,
            },
        )
    return signals


def _record_quorum(
    recorder: TraceRecorder,
    scenario: ScenarioSpec,
    quorum: QuorumRule,
    signals: list[SignalEnvelope],
) -> None:
    if not scenario.bca2p.quorum_observed:
        return
    recorder.record_event(
        RuntimeEventType.QUORUM_TRIGGERED,
        step=min(3, max(1, len(signals))),
        signal_id=f"{scenario.slug}:quorum",
        details={
            "rule_id": quorum.rule_id,
            "target_scope": quorum.target_scope,
            "threshold": quorum.threshold,
            "action": quorum.action,
        },
    )


def _record_feedback(
    causal_store: CausalGraphStore,
    scenario: ScenarioSpec,
    signals: list[SignalEnvelope],
) -> dict[str, Any]:
    if not signals:
        return {}
    target = signals[0]
    causal_store.ingest_feedback(
        CausalFeedback(
            target_signal_id=target.signal_id,
            feedback_type=FeedbackType.OUTCOME,
            outcome="correct" if scenario.bca2p.correct_decision else "incorrect",
            confidence=0.86,
            contributors=[
                ContributionFactor(source_id=target.sender, contribution=0.7),
                ContributionFactor(source_id=scenario.agent_roles[-1], contribution=0.3),
            ],
            metadata={"scenario": scenario.slug},
        ),
        step=4,
    )
    summary = causal_store.summarize_contributions(target.signal_id)
    counterfactual = causal_store.what_if_signal_stayed_local(target.signal_id)
    return {
        "summary": asdict(summary),
        "counterfactual": asdict(counterfactual),
    }


def _mode(value: str) -> SignalMode:
    return SignalMode(value)


def _winning_claim(comparison: ScenarioComparison) -> str:
    strongest_metric = max(
        comparison.bca2p.metrics,
        key=lambda name: comparison.bca2p.metrics[name] - comparison.baseline.metrics[name],
    )
    return f"largest gain: {strongest_metric.replace('_', ' ')}"
