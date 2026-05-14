"""Command-line entrypoint for the bca2p coordination benchmark."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for _path in (ROOT, SRC):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)

from examples.benchmarks.render import render_leaderboard, render_summary_report  # noqa: E402
from examples.benchmarks.runners import run_coordination_benchmarks  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the bca2p coordination benchmark")
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Output format for stdout",
    )
    parser.add_argument(
        "--write-reports",
        action="store_true",
        help="Write leaderboard.md and reports/benchmark_summary.md",
    )
    args = parser.parse_args(argv)

    comparisons = run_coordination_benchmarks()
    if args.write_reports:
        (ROOT / "leaderboard.md").write_text(render_leaderboard(comparisons), encoding="utf-8")
        reports_dir = ROOT / "reports"
        reports_dir.mkdir(exist_ok=True)
        (reports_dir / "benchmark_summary.md").write_text(
            render_summary_report(comparisons),
            encoding="utf-8",
        )

    if args.format == "markdown":
        print(render_leaderboard(comparisons))
    else:
        print(json.dumps(_json_payload(comparisons), indent=2, sort_keys=True))
    return 0


def _json_payload(comparisons: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "scenario": comparison.scenario.slug,
            "use_case": comparison.scenario.use_case,
            "dataset": comparison.scenario.dataset,
            "baseline": {
                "score": comparison.baseline.score,
                "metrics": comparison.baseline.metrics,
                "measurements": asdict(comparison.baseline.measurements),
            },
            "bca2p": {
                "score": comparison.bca2p.score,
                "metrics": comparison.bca2p.metrics,
                "measurements": asdict(comparison.bca2p.measurements),
            },
            "score_delta": comparison.score_delta,
        }
        for comparison in comparisons
    ]


if __name__ == "__main__":
    raise SystemExit(main())
