from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from bca2p.core import ComplexSpec, HomeostasisPolicy, QuorumRule, ReceptorSpec, SignalMode
from bca2p.graph import (
    AggregateChannel,
    BioGraph,
    BioNode,
    ComplexLifecycleState,
    EphemeralChannel,
    GraphValidationError,
    LastValueChannel,
    TopicChannel,
)


class ResearchPayload(BaseModel):
    query: str


def noop_handler(state: Any, context: Any) -> dict[str, Any]:
    context.emitter.emit(
        mode=SignalMode.PARACRINE,
        recipient_scope="research.team",
        receptor="research.query",
        payload={"query": "map patents"},
    )
    return {"ok": True, "state": state}


async def async_handler(state: Any, context: Any) -> dict[str, Any]:
    return {"state": state, "node": context.node_id}


def test_last_value_channel_keeps_latest_update() -> None:
    channel = LastValueChannel(name="latest", value="old")
    result = channel.apply_updates(["new-1", "new-2"])
    assert result == "new-2"
    assert channel.read() == "new-2"


def test_topic_channel_accumulates_and_can_deduplicate() -> None:
    channel = TopicChannel(name="events", deduplicate=True)
    channel.apply_updates(["a", "a", "b"])
    assert channel.read() == ["a", "b"]
    channel.apply_updates(["b", "c"])
    assert channel.read() == ["a", "b", "c"]


def test_aggregate_channel_uses_reducer() -> None:
    channel = AggregateChannel(name="counter", reducer=lambda left, right: (left or 0) + right, initial_value=0)
    result = channel.apply_updates([1, 2, 3])
    assert result == 6
    assert channel.read() == 6


def test_ephemeral_channel_resets() -> None:
    channel = EphemeralChannel(name="ephemeral")
    channel.apply_updates(["value"])
    assert channel.read() == "value"
    channel.reset()
    assert channel.read() is None


def test_bionode_detects_async_and_matches_signal_routes() -> None:
    receptor = ReceptorSpec.from_payload_model(
        receptor_id="research.query",
        payload_model=ResearchPayload,
        accepted_modes=[SignalMode.PARACRINE],
    )
    node = BioNode(
        node_id="researcher",
        handler=async_handler,
        receptors=[receptor],
        scope_subscriptions=["research.*"],
        topology_subscriptions=["local-cluster"],
    )

    assert node.is_async is True
    context = node.create_context()
    assert context.node_id == "researcher"

    signal = context.emitter.emit(
        mode=SignalMode.PARACRINE,
        recipient_scope="research.team",
        receptor="research.query",
        payload={"query": "map patents"},
        policy_tags=["local-cluster"],
    )
    assert node.matches_signal(signal) is True


def test_biograph_compile_produces_compiled_complexes_with_pending_state() -> None:
    graph = BioGraph(metadata={"scopes": ["research.team"]})
    graph.add_channel("signals", mode="topic")
    graph.add_agent(
        "planner",
        noop_handler,
        scope_subscriptions=["research.team"],
        output_channel="signals",
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
            threshold=0.6,
        )
    )
    graph.add_homeostasis(HomeostasisPolicy.default())

    compiled = graph.compile()
    assert compiled.get_complex_state("research_complex") == ComplexLifecycleState.PENDING
    compiled.set_complex_state("research_complex", ComplexLifecycleState.ACTIVE)
    assert compiled.get_complex_state("research_complex") == ComplexLifecycleState.ACTIVE


def test_biograph_validation_rejects_duplicate_receptor_ids() -> None:
    graph = BioGraph()
    graph.add_agent(
        "agent-a",
        noop_handler,
        receptors=[
            ReceptorSpec.from_payload_model(
                receptor_id="dup.receptor",
                payload_model=ResearchPayload,
                accepted_modes=[SignalMode.PARACRINE],
            )
        ],
    )
    graph.add_agent(
        "agent-b",
        noop_handler,
        receptors=[
            ReceptorSpec.from_payload_model(
                receptor_id="dup.receptor",
                payload_model=ResearchPayload,
                accepted_modes=[SignalMode.SYNAPTIC],
            )
        ],
    )
    with pytest.raises(GraphValidationError):
        graph.compile()


def test_biograph_validation_rejects_missing_channel_references() -> None:
    graph = BioGraph(metadata={"scopes": ["research.team"]})
    graph.add_agent(
        "planner",
        noop_handler,
        scope_subscriptions=["research.team"],
        output_channel="missing-channel",
    )
    with pytest.raises(GraphValidationError):
        graph.compile()


def test_biograph_validation_rejects_unknown_quorum_scope() -> None:
    graph = BioGraph()
    graph.add_channel("signals", mode="topic")
    graph.add_agent(
        "planner",
        noop_handler,
        input_channels=["signals"],
    )
    graph.add_quorum_rule(
        QuorumRule(
            rule_id="bad_quorum",
            target_scope="unknown.scope",
            threshold=0.5,
        )
    )
    with pytest.raises(GraphValidationError):
        graph.compile()


def test_biograph_validation_rejects_orphan_agents() -> None:
    graph = BioGraph()
    graph.add_agent("orphan", noop_handler)
    with pytest.raises(GraphValidationError):
        graph.compile()


def test_add_channel_rejects_invalid_modes_and_missing_aggregate_reducer() -> None:
    graph = BioGraph()
    with pytest.raises(GraphValidationError):
        graph.add_channel("agg", mode="aggregate")
    with pytest.raises(GraphValidationError):
        graph.add_channel("bad", mode="unknown")


def test_compiled_graph_can_find_matching_nodes_for_signal() -> None:
    graph = BioGraph(metadata={"scopes": ["research.team"]})
    graph.add_channel("signals", mode="topic")
    graph.add_agent(
        "planner",
        noop_handler,
        scope_subscriptions=["research.team"],
        output_channel="signals",
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
        scope_subscriptions=["research.team"],
    )
    compiled = graph.compile()
    signal = compiled.get_node("planner").create_context().emitter.emit(
        mode=SignalMode.PARACRINE,
        recipient_scope="research.team",
        receptor="research.query",
        payload={"query": "map patents"},
    )
    matching = [node.node_id for node in compiled.matching_nodes_for_signal(signal)]
    assert matching == ["planner", "researcher"]
