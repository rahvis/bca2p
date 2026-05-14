"""Coordination benchmark examples for bca2p."""

from .models import ApproachResult, LeaderboardEntry, ScenarioComparison, ScenarioSpec
from .render import render_leaderboard, render_summary_report
from .runners import build_leaderboard, run_coordination_benchmarks, run_scenario
from .scenarios import SCENARIOS

__all__ = [
    "SCENARIOS",
    "ApproachResult",
    "LeaderboardEntry",
    "ScenarioComparison",
    "ScenarioSpec",
    "build_leaderboard",
    "render_leaderboard",
    "render_summary_report",
    "run_coordination_benchmarks",
    "run_scenario",
]
