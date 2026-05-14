"""Deterministic coordination scoring for benchmark scenarios."""

from __future__ import annotations

from .models import CoordinationMeasurements, ScenarioSpec

METRIC_WEIGHTS = {
    "task_correctness": 0.30,
    "routing_precision": 0.15,
    "communication_efficiency": 0.15,
    "escalation_quality": 0.15,
    "stability": 0.10,
    "replayability": 0.10,
    "causal_usefulness": 0.05,
}


def bounded(value: float) -> float:
    return max(0.0, min(1.0, value))


def calculate_metric_scores(
    spec: ScenarioSpec,
    measurements: CoordinationMeasurements,
) -> dict[str, float]:
    """Return normalized metric scores in the 0.0-1.0 range."""

    delivered = measurements.relevant_deliveries + measurements.irrelevant_deliveries
    routing_precision = (
        measurements.relevant_deliveries / delivered
        if delivered > 0
        else 0.0
    )

    message_pressure = (
        measurements.total_messages + measurements.duplicate_work_units
    ) / spec.message_ceiling
    token_pressure = measurements.context_tokens / spec.token_ceiling
    latency_pressure = measurements.latency_ms / spec.latency_ceiling_ms
    communication_efficiency = 1.0 - (
        (message_pressure * 0.5) + (token_pressure * 0.3) + (latency_pressure * 0.2)
    )

    escalation_quality = _score_escalation(spec, measurements)
    instability = (
        measurements.retry_storms
        + measurements.route_flaps
        + measurements.amplification_events
    )
    stability = 1.0 - (instability / spec.stability_ceiling)

    replayability = min(
        1.0,
        (0.45 if measurements.replay_artifacts > 0 else 0.0)
        + (0.30 if measurements.evidence_artifacts > 0 else 0.0)
        + (0.25 if measurements.quorum_observed else 0.0),
    )
    causal_usefulness = min(
        1.0,
        ((measurements.causal_links * 0.5) + (measurements.feedback_records * 0.5)) / 2.0,
    )

    return {
        "task_correctness": 1.0 if measurements.correct_decision else 0.0,
        "routing_precision": bounded(routing_precision),
        "communication_efficiency": bounded(communication_efficiency),
        "escalation_quality": bounded(escalation_quality),
        "stability": bounded(stability),
        "replayability": bounded(replayability),
        "causal_usefulness": bounded(causal_usefulness),
    }


def calculate_coordination_score(
    spec: ScenarioSpec,
    measurements: CoordinationMeasurements,
) -> float:
    metrics = calculate_metric_scores(spec, measurements)
    weighted = sum(metrics[name] * weight for name, weight in METRIC_WEIGHTS.items())
    return round(weighted * 100.0, 2)


def _score_escalation(
    spec: ScenarioSpec,
    measurements: CoordinationMeasurements,
) -> float:
    if measurements.should_escalate and not measurements.escalated:
        return 0.0
    if not measurements.should_escalate and measurements.escalated:
        return 0.0

    delay_penalty = measurements.escalation_delay_steps / max(1, spec.deadline_steps)
    incident_penalty = (
        (measurements.false_escalations * 0.35)
        + (measurements.missed_escalations * 0.45)
        + (delay_penalty * 0.20)
    )
    return 1.0 - incident_penalty
