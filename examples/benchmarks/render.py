"""Markdown renderers for benchmark artifacts."""

from __future__ import annotations

from statistics import mean

from .models import LeaderboardEntry, ScenarioComparison
from .runners import build_leaderboard


def render_leaderboard(comparisons: list[ScenarioComparison]) -> str:
    entries = build_leaderboard(comparisons)
    lines = [
        "# bca2p Coordination Benchmark Leaderboard",
        "",
        "This leaderboard is generated from deterministic benchmark fixtures. Scores are "
        "0-100 and do not depend on an LLM judge.",
        "",
        "| Rank | Use case | Dataset | Baseline | bca2p | Delta | Claim |",
        "|---:|---|---|---:|---:|---:|---|",
    ]
    lines.extend(_entry_row(entry) for entry in entries)
    lines.extend(
        [
            "",
            "## Aggregate",
            "",
            f"- Average baseline score: {_average_baseline(entries):.2f}",
            f"- Average bca2p score: {_average_bca2p(entries):.2f}",
            f"- Average improvement: {_average_delta(entries):.2f}",
            "",
            "## Reproduce",
            "",
            "```bash",
            "PYTHONPATH=src python3 examples/benchmarks/app.py --format markdown",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def render_summary_report(comparisons: list[ScenarioComparison]) -> str:
    lines = [
        "# bca2p Coordination Benchmark Summary",
        "",
        "The deterministic benchmark isolates communication mechanics from model quality. "
        "Each scenario compares plain multi-agent messaging with bca2p typed signaling "
        "under the same use case, agent roles, task input, and ground-truth decision.",
        "",
    ]
    for comparison in comparisons:
        lines.extend(
            [
                f"## {comparison.scenario.use_case}",
                "",
                f"- Dataset: {comparison.scenario.dataset}",
                f"- Ground truth: {comparison.scenario.ground_truth}",
                f"- Baseline score: {comparison.baseline.score:.2f}",
                f"- bca2p score: {comparison.bca2p.score:.2f}",
                f"- Delta: {comparison.score_delta:.2f}",
                f"- Strongest claim: {build_leaderboard([comparison])[0].winning_claim}",
                "",
            ]
        )
    return "\n".join(lines)


def _entry_row(entry: LeaderboardEntry) -> str:
    return (
        f"| {entry.rank} | {entry.use_case} | {entry.dataset} | "
        f"{entry.baseline_score:.2f} | {entry.bca2p_score:.2f} | "
        f"{entry.score_delta:.2f} | {entry.winning_claim} |"
    )


def _average_baseline(entries: list[LeaderboardEntry]) -> float:
    return mean(entry.baseline_score for entry in entries)


def _average_bca2p(entries: list[LeaderboardEntry]) -> float:
    return mean(entry.bca2p_score for entry in entries)


def _average_delta(entries: list[LeaderboardEntry]) -> float:
    return mean(entry.score_delta for entry in entries)
