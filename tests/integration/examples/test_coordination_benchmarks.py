from __future__ import annotations

from examples.benchmarks import SCENARIOS, build_leaderboard, run_coordination_benchmarks
from examples.benchmarks.gemini import GeminiAgentConfig, GeminiStructuredAgent
from examples.benchmarks.scoring import METRIC_WEIGHTS


def test_coordination_benchmark_covers_all_risk_sensitive_use_cases() -> None:
    comparisons = run_coordination_benchmarks()

    assert len(comparisons) == 9
    assert {comparison.scenario.slug for comparison in comparisons} == {
        scenario.slug for scenario in SCENARIOS
    }
    assert all(comparison.bca2p.score > comparison.baseline.score for comparison in comparisons)


def test_coordination_metrics_are_weighted_to_one() -> None:
    assert round(sum(METRIC_WEIGHTS.values()), 6) == 1.0


def test_cyber_scenario_exposes_bca2p_trace_and_causal_artifacts() -> None:
    comparison = next(
        item
        for item in run_coordination_benchmarks()
        if item.scenario.slug == "cyber_incident_response"
    )

    assert comparison.bca2p.trace["communication_style"] == "typed bca2p signaling"
    assert comparison.bca2p.trace["runtime_event_counts"]["signal_emitted"] > 0
    assert comparison.bca2p.trace["runtime_event_counts"]["signal_delivered"] > 0
    assert comparison.bca2p.trace["runtime_event_counts"]["quorum_triggered"] == 1
    assert comparison.bca2p.trace["replay_bundle"]["checkpoint_ids"]
    assert comparison.bca2p.trace["causal_summary"]["counterfactual"]["target_signal_id"]


def test_leaderboard_ranks_by_bca2p_score() -> None:
    entries = build_leaderboard(run_coordination_benchmarks())
    scores = [entry.bca2p_score for entry in entries]

    assert scores == sorted(scores, reverse=True)
    assert entries[0].use_case == "Cyber incident response"


def test_gemini_agent_uses_runtime_key_configuration_without_reading_env() -> None:
    agent = GeminiStructuredAgent(
        role="risk_agent",
        output_schema={
            "type": "object",
            "properties": {"decision": {"type": "string"}},
            "required": ["decision"],
        },
        config=GeminiAgentConfig(model="gemini-2.5-flash"),
    )

    assert agent.config.api_key_env == "GEMINI_API_KEY"
    assert agent.config.model == "gemini-2.5-flash"
