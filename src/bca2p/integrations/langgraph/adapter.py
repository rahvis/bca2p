"""LangGraph adapter boundary for bca2p graphs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from bca2p.graph import AggregateChannel, BioGraph, BioNode, EphemeralChannel, LastValueChannel, TopicChannel


@dataclass(slots=True)
class LangGraphChannelMapping:
    """Mapping from a bca2p channel to LangGraph runtime semantics."""

    channel_name: str
    langgraph_kind: str
    state_key: str


@dataclass(slots=True)
class LangGraphComplexBranch:
    """Representation of a temporary collaboration branch/subgraph."""

    scaffold_id: str
    members: list[str]
    shared_state_key: str | None


class LangGraphAdapter:
    """Adapter for translating ``BioGraph`` authoring constructs to LangGraph."""

    def __init__(self, graph: BioGraph) -> None:
        self.graph = graph

    def state_key_for_channel(self, channel_name: str) -> str:
        return f"bca2p__channel__{channel_name}"

    def map_channel(self, channel_name: str) -> LangGraphChannelMapping:
        channel = self.graph.channels[channel_name]
        if isinstance(channel, TopicChannel):
            kind = "topic"
        elif isinstance(channel, LastValueChannel):
            kind = "last_value"
        elif isinstance(channel, AggregateChannel):
            kind = "aggregate"
        elif isinstance(channel, EphemeralChannel):
            kind = "ephemeral"
        else:
            kind = "unknown"
        return LangGraphChannelMapping(
            channel_name=channel_name,
            langgraph_kind=kind,
            state_key=self.state_key_for_channel(channel_name),
        )

    def map_channels(self) -> dict[str, LangGraphChannelMapping]:
        return {name: self.map_channel(name) for name in self.graph.channels}

    def state_key_map(self) -> dict[str, str]:
        return {name: self.state_key_for_channel(name) for name in self.graph.channels}

    def build_signal_node(self, node_id: str) -> Any:
        node = self.graph.nodes[node_id]
        channel_map = self.state_key_map()

        def langgraph_node(state: dict[str, Any]) -> dict[str, Any]:
            context = node.create_context()
            result = node.invoke(state, context=context)
            if hasattr(result, "__await__"):
                raise RuntimeError("Async node wrappers must be awaited by the host runtime")

            update: dict[str, Any] = {
                "__bca2p_emitted_signals__": [signal.to_dict() for signal in context.emitter.emitted_signals],
                "__bca2p_trace_metadata__": {
                    "node_id": node.node_id,
                    "matched_receptors": node.receptor_ids(),
                },
            }
            if node.output_channel is not None and result is not None:
                update[channel_map[node.output_channel]] = result
            return update

        return langgraph_node

    def complex_branch(self, scaffold_id: str) -> LangGraphComplexBranch:
        complex_spec = self.graph._complexes[scaffold_id]  # noqa: SLF001
        shared_state_key = (
            self.state_key_for_channel(complex_spec.shared_state_channel)
            if complex_spec.shared_state_channel is not None
            else None
        )
        return LangGraphComplexBranch(
            scaffold_id=scaffold_id,
            members=list(complex_spec.members),
            shared_state_key=shared_state_key,
        )

    def compile_to_langgraph(self, *, checkpointer: Any | None = None) -> Any:
        try:
            from langgraph.graph import END, START, StateGraph  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("LangGraph is not available in the current environment") from exc

        state_graph = StateGraph(dict)
        for node_id in self.graph.nodes:
            state_graph.add_node(node_id, self.build_signal_node(node_id))

        for node in self.graph.nodes.values():
            if not node.input_channels or node.metadata.get("entrypoint") is True:
                state_graph.add_edge(START, node.node_id)
            if not node.output_channel:
                state_graph.add_edge(node.node_id, END)
                continue
            for downstream in self.graph.nodes.values():
                if node.output_channel in downstream.input_channels:
                    state_graph.add_edge(node.node_id, downstream.node_id)

        compiled = state_graph.compile(checkpointer=checkpointer)
        return {
            "compiled_graph": compiled,
            "state_key_map": self.state_key_map(),
            "complex_branches": {
                scaffold_id: self.complex_branch(scaffold_id)
                for scaffold_id in self.graph._complexes  # noqa: SLF001
            },
        }
