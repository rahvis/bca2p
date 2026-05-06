from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from pydantic import BaseModel

from bca2p.core import ComplexSpec, HomeostasisPolicy, QuorumRule, ReceptorSpec, SignalMode
from bca2p.graph import BioGraph, ComplexLifecycleState
from bca2p.observability import TraceRecorder, detect_bottlenecks, noisy_sender_report
from bca2p.runtime import BioRuntime, FileCheckpointer, InMemoryCheckpointer, RuntimeConfig


class ResearchPayload(BaseModel):
    query: str


def planner_handler(state: dict[str, Any], context: Any) -> dict[str, Any]:
    context.emitter.emit(
        mode=SignalMode.PARACRINE,
        recipient_scope="research.team",
        receptor="research.query",
        payload={"query": "map patents"},
        ttl=3.0,
        decay=0.25,
        amplification=200.0,
    )
    return {"planner_status": "planned", "step": state["__step__"]}


def researcher_handler(state: dict[str, Any], context: Any) -> dict[str, Any]:
    matched_signals = state["__signals__"]
    query = matched_signals[0]["payload"]["query"] if matched_signals else "none"
    return {
        "research_status": "researched",
        "query": query,
        "channel_state": state["__channels__"].get("planner_updates"),
    }


def build_runtime(checkpointer: InMemoryCheckpointer | FileCheckpointer | None = None) -> BioRuntime:
    graph = BioGraph(metadata={"scopes": ["research.team"]})
    graph.add_channel("planner_updates", mode="last_value")
    graph.add_channel("research_updates", mode="last_value")
    graph.add_channel("signal_log", mode="topic")
    graph.add_agent(
        "planner",
        planner_handler,
        scope_subscriptions=["research.team"],
        output_channel="planner_updates",
        metadata={"entrypoint": True},
    )
    graph.add_agent(
        "researcher",
        researcher_handler,
        receptors=[
            ReceptorSpec.from_payload_model(
                receptor_id="research.query",
                payload_model=ResearchPayload,
                accepted_modes=[SignalMode.PARACRINE, SignalMode.QUORUM],
            )
        ],
        input_channels=["planner_updates"],
        scope_subscriptions=["research.team"],
        output_channel="research_updates",
    )
    graph.add_complex_policy(
        ComplexSpec(
            scaffold_id="research_complex",
            members=["planner", "researcher"],
            shared_state_channel="planner_updates",
        )
    )
    graph.add_quorum_rule(
        QuorumRule(
            rule_id="research_consensus",
            target_scope="research.team",
            threshold=1.0,
            min_participants=1,
        )
    )
    graph.add_homeostasis(HomeostasisPolicy.default())
    compiled = graph.compile(max_steps=5)
    return BioRuntime(
        compiled,
        checkpointer=checkpointer,
        config=RuntimeConfig(max_steps=5, max_retries=0),
    )


def test_runtime_executes_multi_step_workflow_and_checkpoints_history() -> None:
    runtime = build_runtime()
    result = runtime.invoke({"workflow_id": "wf-1"})

    assert result.completed is True
    assert result.steps_executed >= 2
    assert result.final_state["planner_updates"]["planner_status"] == "planned"
    assert result.final_state["research_updates"]["research_status"] == "researched"

    history = runtime.get_state_history()
    assert len(history) >= 2
    assert history[0].active_nodes == ["planner"]
    assert history[1].active_nodes == ["researcher"]
    assert history[0].pending_signals
    assert history[0].pending_signals[0].amplification == 80.0


def test_runtime_replay_and_fork_replay_use_saved_checkpoints() -> None:
    runtime = build_runtime()
    result = runtime.invoke({"workflow_id": "wf-2"})
    history = runtime.get_state_history()

    replay_result = runtime.replay(history[0].snapshot_id)
    assert replay_result.completed is True

    fork_result = runtime.fork_replay(
        history[0].snapshot_id,
        state_update={"forked": True},
        as_node="researcher",
    )
    assert fork_result.final_state["forked"] is True
    assert fork_result.completed is True
    assert fork_result.final_snapshot is not None
    assert fork_result.final_snapshot.metadata["context"]["fork_as_node"] == "researcher"
    assert result.final_snapshot is not None


def test_runtime_file_checkpointer_persists_snapshots() -> None:
    with TemporaryDirectory() as temp_dir:
        checkpointer = FileCheckpointer(Path(temp_dir))
        runtime = build_runtime(checkpointer=checkpointer)
        result = runtime.invoke({"workflow_id": "wf-3"})

        assert result.final_snapshot is not None
        loaded = checkpointer.get(result.final_snapshot.snapshot_id)
        assert loaded is not None
        assert loaded.snapshot_id == result.final_snapshot.snapshot_id
        assert checkpointer.history()


def test_runtime_updates_complex_lifecycle_during_execution() -> None:
    runtime = build_runtime()
    result = runtime.invoke({"workflow_id": "wf-4"})
    assert result.final_snapshot is not None
    assert result.final_snapshot.complex_states["research_complex"] in {
        ComplexLifecycleState.ACTIVE,
        ComplexLifecycleState.COMPLETED,
    }


def test_runtime_emits_observability_events_and_topology_snapshots() -> None:
    recorder = TraceRecorder(trace_id="runtime-trace")
    runtime = build_runtime()
    runtime.trace_recorder = recorder

    result = runtime.invoke({"workflow_id": "wf-5"})

    assert result.final_snapshot is not None
    assert recorder.events
    assert recorder.topology_timeline
    assert any(event.event_type.value == "signal_emitted" for event in recorder.events)
    assert any(event.event_type.value == "signal_delivered" for event in recorder.events)
    assert detect_bottlenecks(recorder.events)
    assert noisy_sender_report(recorder.events)
