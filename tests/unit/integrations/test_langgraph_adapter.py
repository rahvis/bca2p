from __future__ import annotations

import sys
import types

from pydantic import BaseModel

from bca2p.core import ComplexSpec, ReceptorSpec, SignalMode
from bca2p.graph import BioGraph
from bca2p.integrations.langgraph import LangGraphAdapter


class ResearchPayload(BaseModel):
    query: str


def handler(state, context):
    context.emitter.emit(
        mode=SignalMode.PARACRINE,
        recipient_scope="research.team",
        receptor="research.query",
        payload={"query": "map patents"},
    )
    return {"status": "ok"}


def build_graph() -> BioGraph:
    graph = BioGraph(metadata={"scopes": ["research.team"]})
    graph.add_channel("signals", mode="topic")
    graph.add_channel("results", mode="last_value")
    graph.add_agent(
        "planner",
        handler,
        scope_subscriptions=["research.team"],
        output_channel="signals",
        metadata={"entrypoint": True},
    )
    graph.add_agent(
        "researcher",
        handler,
        receptors=[
            ReceptorSpec.from_payload_model(
                receptor_id="research.query",
                payload_model=ResearchPayload,
                accepted_modes=[SignalMode.PARACRINE],
            )
        ],
        input_channels=["signals"],
        output_channel="results",
    )
    graph.add_complex_policy(
        ComplexSpec(
            scaffold_id="research_complex",
            members=["planner", "researcher"],
            shared_state_channel="signals",
        )
    )
    return graph


def test_langgraph_adapter_maps_channels_and_state_keys() -> None:
    adapter = LangGraphAdapter(build_graph())
    mappings = adapter.map_channels()
    assert mappings["signals"].langgraph_kind == "topic"
    assert mappings["results"].langgraph_kind == "last_value"
    assert adapter.state_key_map()["signals"] == "bca2p__channel__signals"


def test_langgraph_signal_node_wraps_bionode_output() -> None:
    adapter = LangGraphAdapter(build_graph())
    node = adapter.build_signal_node("planner")
    result = node({"workflow_id": "wf-1"})
    assert "__bca2p_emitted_signals__" in result
    assert result["bca2p__channel__signals"]["status"] == "ok"


def test_langgraph_complex_branch_maps_shared_state() -> None:
    adapter = LangGraphAdapter(build_graph())
    branch = adapter.complex_branch("research_complex")
    assert branch.shared_state_key == "bca2p__channel__signals"


def test_langgraph_compile_uses_fake_stategraph(monkeypatch) -> None:
    calls: dict[str, list] = {"nodes": [], "edges": []}

    class FakeCompiled:
        def __init__(self, checkpointer):
            self.checkpointer = checkpointer

    class FakeStateGraph:
        def __init__(self, state_type):
            self.state_type = state_type

        def add_node(self, name, fn):
            calls["nodes"].append((name, fn))

        def add_edge(self, left, right):
            calls["edges"].append((left, right))

        def compile(self, checkpointer=None):
            return FakeCompiled(checkpointer)

    fake_module = types.ModuleType("langgraph.graph")
    fake_module.StateGraph = FakeStateGraph
    fake_module.START = "START"
    fake_module.END = "END"

    monkeypatch.setitem(sys.modules, "langgraph", types.ModuleType("langgraph"))
    monkeypatch.setitem(sys.modules, "langgraph.graph", fake_module)

    adapter = LangGraphAdapter(build_graph())
    compiled = adapter.compile_to_langgraph(checkpointer="memory")
    assert compiled["compiled_graph"].checkpointer == "memory"
    assert calls["nodes"]
    assert calls["edges"]
