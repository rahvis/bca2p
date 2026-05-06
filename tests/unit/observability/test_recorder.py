from __future__ import annotations

import json

from pydantic import BaseModel

from bca2p.core import ComplexSpec, QuorumRule, ReceptorSpec, SignalMode
from bca2p.graph import BioGraph
from bca2p.observability import (
    RuntimeEventType,
    TraceRecorder,
    amplification_storm_report,
    detect_bottlenecks,
    dormant_receptor_report,
    noisy_sender_report,
)


class ResearchPayload(BaseModel):
    query: str


def noop_handler(state, context):
    context.emitter.emit(
        mode=SignalMode.PARACRINE,
        recipient_scope="research.team",
        receptor="research.query",
        payload={"query": "map patents"},
        amplification=25.0,
    )
    return {"status": "ok"}


def build_graph():
    graph = BioGraph(metadata={"scopes": ["research.team"]})
    graph.add_channel("signals", mode="topic")
    graph.add_agent(
        "planner",
        noop_handler,
        scope_subscriptions=["research.team"],
        output_channel="signals",
        metadata={"entrypoint": True},
    )
    graph.add_agent(
        "researcher",
        noop_handler,
        receptors=[
            ReceptorSpec.from_payload_model(
                receptor_id="research.query",
                payload_model=ResearchPayload,
                accepted_modes=[SignalMode.PARACRINE],
            )
        ],
        input_channels=["signals"],
        scope_subscriptions=["research.team"],
    )
    graph.add_complex_policy(
        ComplexSpec(
            scaffold_id="research_complex",
            members=["planner", "researcher"],
            shared_state_channel="signals",
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
    return graph.compile()


def test_trace_recorder_builds_bundle_json_and_visualization() -> None:
    recorder = TraceRecorder(trace_id="trace-observe")
    recorder.record_event(
        RuntimeEventType.SIGNAL_EMITTED,
        step=0,
        node_id="planner",
        signal_id="sig-1",
        details={"sender": "planner", "recipient_scope": "research.team", "amplification": 25.0},
    )
    recorder.record_event(
        RuntimeEventType.SIGNAL_DELIVERED,
        step=1,
        node_id="researcher",
        signal_id="sig-1",
        details={"sender": "planner", "receptor": "research.query"},
    )
    recorder.record_topology_snapshot(build_graph(), step=0)

    payload = json.loads(recorder.to_json(checkpoint_ids=["checkpoint-0001"]))
    assert payload["trace_id"] == "trace-observe"
    assert payload["checkpoint_ids"] == ["checkpoint-0001"]
    assert payload["events"][0]["event_type"] == "signal_emitted"

    viz = recorder.build_visualization_graph()
    assert viz.nodes
    assert viz.edges


def test_diagnostics_detect_bottlenecks_noise_dormant_and_storms() -> None:
    recorder = TraceRecorder()
    recorder.record_event(
        RuntimeEventType.SIGNAL_EMITTED,
        step=0,
        node_id="planner",
        signal_id="sig-1",
        details={"sender": "planner", "recipient_scope": "research.team", "amplification": 30.0},
    )
    recorder.record_event(
        RuntimeEventType.SIGNAL_EMITTED,
        step=1,
        node_id="planner",
        signal_id="sig-2",
        details={"sender": "planner", "recipient_scope": "research.team", "amplification": 12.0},
    )
    recorder.record_event(
        RuntimeEventType.SIGNAL_DELIVERED,
        step=1,
        node_id="researcher",
        signal_id="sig-1",
        details={"sender": "planner", "receptor": "research.query"},
    )
    recorder.record_event(
        RuntimeEventType.SIGNAL_DELIVERED,
        step=2,
        node_id="researcher",
        signal_id="sig-2",
        details={"sender": "planner", "receptor": "research.query"},
    )

    graph = build_graph()
    assert detect_bottlenecks(recorder.events)
    assert noisy_sender_report(recorder.events)
    assert amplification_storm_report(recorder.events, amplification_threshold=10.0)
    dormant = dormant_receptor_report(graph, recorder.events)
    assert dormant == []
