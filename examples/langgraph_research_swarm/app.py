from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for _path in (ROOT, SRC):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)

from pydantic import BaseModel

from bca2p.core import ComplexSpec, QuorumRule, ReceptorSpec, SignalMode
from bca2p.graph import BioGraph
from bca2p.integrations.langgraph import LangGraphAdapter


class ResearchPayload(BaseModel):
    query: str


def planner_handler(state, context):
    context.emitter.emit(
        mode=SignalMode.ENDOCRINE,
        recipient_scope="research.team",
        receptor="research.query",
        payload={"query": "map the patent landscape for bio-inspired agent communication"},
        policy_tags=["complex:research_cluster"],
    )
    return {"planner_status": "planned"}


def researcher_handler(state, context):
    return {"research_status": "researched", "seen_signals": state.get("__signals__", [])}


def critic_handler(state, context):
    return {"critic_status": "reviewed", "seen_signals": state.get("__signals__", [])}


def build_biograph() -> BioGraph:
    graph = BioGraph(metadata={"scopes": ["research.team"]})
    graph.add_channel("signals", mode="topic")
    graph.add_channel("research", mode="last_value")
    graph.add_channel("critique", mode="last_value")

    graph.add_agent(
        "planner",
        planner_handler,
        scope_subscriptions=["research.team"],
        output_channel="signals",
        metadata={"entrypoint": True},
    )
    graph.add_agent(
        "researcher",
        researcher_handler,
        receptors=[
            ReceptorSpec.from_payload_model(
                receptor_id="research.query",
                payload_model=ResearchPayload,
                accepted_modes=[SignalMode.ENDOCRINE, SignalMode.PARACRINE],
            )
        ],
        input_channels=["signals"],
        output_channel="research",
    )
    graph.add_agent(
        "critic",
        critic_handler,
        scope_subscriptions=["research.team"],
        input_channels=["research"],
        output_channel="critique",
    )
    graph.add_complex_policy(
        ComplexSpec(
            scaffold_id="research_eval",
            members=["planner", "researcher", "critic"],
            shared_state_channel="signals",
        )
    )
    graph.add_quorum_rule(
        QuorumRule(
            rule_id="research_consensus",
            target_scope="research.team",
            threshold=1.0,
            min_participants=1,
            action="proceed",
        )
    )
    return graph


def build_langgraph_adapter() -> LangGraphAdapter:
    return LangGraphAdapter(build_biograph())


if __name__ == "__main__":
    adapter = build_langgraph_adapter()
    print(adapter.state_key_map())
