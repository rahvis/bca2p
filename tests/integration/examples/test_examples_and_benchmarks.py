from __future__ import annotations

import asyncio

from examples.benchmark_harness import run_benchmarks
from examples.cell_simulation.app import run_cell_simulation_example
from examples.langchain_support_swarm.app import run_support_swarm
from examples.langchain_support_swarm.standard import run_standard_support_swarm
from examples.langgraph_research_swarm.standard import run_standard_research_swarm
from examples.marl_training.app import run_training_example
from examples.native_runtime.app import run_native_example
from examples.langgraph_research_swarm.app import build_biograph

from bca2p.native import NativeBioRuntime
from bca2p.runtime import BioRuntime, RuntimeConfig


def test_stable_examples_and_benchmark_harness_run() -> None:
    standard_research = run_standard_research_swarm()
    standard_support = run_standard_support_swarm("ticket-1")
    bca2p_support = asyncio.run(run_support_swarm("ticket-1"))
    marl_result = run_training_example()
    sim_result = run_cell_simulation_example()
    native_result = run_native_example()
    benchmarks = run_benchmarks()

    assert standard_research["communication_style"] == "free-form natural language"
    assert standard_support["communication_style"] == "tool calls and implicit prompting"
    assert bca2p_support.billing_result["billing_status"] == "resolved"
    assert marl_result["trained_average_reward"] > marl_result["baseline_average_reward"]
    assert sim_result["events"]
    assert native_result["completed"] is True
    assert len(benchmarks) == 4
    assert benchmarks[0].bca2p["routing_clarity"] > benchmarks[0].baseline["routing_clarity"]


def test_native_runtime_parity_with_stable_runtime() -> None:
    graph = build_biograph()
    compiled = graph.compile(max_steps=5)
    stable_result = BioRuntime(compiled, config=RuntimeConfig(max_steps=5)).invoke(
        {"workflow_id": "stable-parity"}
    )
    native_result = NativeBioRuntime.from_graph(
        graph,
        config=RuntimeConfig(max_steps=5),
    ).invoke({"workflow_id": "native-parity"})

    assert stable_result.completed is True
    assert native_result.completed is True
    assert stable_result.final_state.keys() == native_result.final_state.keys()
    assert (
        stable_result.final_state["signals"]["planner_status"]
        == native_result.final_state["signals"]["planner_status"]
    )
    assert (
        stable_result.final_state["research"]["research_status"]
        == native_result.final_state["research"]["research_status"]
    )
