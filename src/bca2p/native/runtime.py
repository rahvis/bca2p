"""Experimental first-party native runtime for bca2p."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from bca2p.graph import CompiledBioGraph
from bca2p.observability import TraceRecorder
from bca2p.runtime import BioRuntime, Checkpointer, InMemoryCheckpointer, RuntimeConfig, RuntimeResult


@dataclass
class NativeCompiledBioGraph:
    """Native compiled graph surface that owns a runtime-ready graph snapshot."""

    graph: CompiledBioGraph
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_compiled_graph(
        cls,
        compiled: CompiledBioGraph,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> "NativeCompiledBioGraph":
        return cls(graph=deepcopy(compiled), metadata=metadata or {})


class NativeBioRuntime(BioRuntime):
    """Native execution engine that reuses the stable runtime semantics."""

    def __init__(
        self,
        compiled_graph: NativeCompiledBioGraph,
        *,
        checkpointer: Checkpointer | None = None,
        config: RuntimeConfig | None = None,
        trace_recorder: TraceRecorder | None = None,
    ) -> None:
        self.native_graph = compiled_graph
        super().__init__(
            compiled_graph.graph,
            checkpointer=checkpointer or InMemoryCheckpointer(),
            config=config,
            trace_recorder=trace_recorder,
        )

    @classmethod
    def from_graph(
        cls,
        graph: Any,
        *,
        checkpointer: Checkpointer | None = None,
        config: RuntimeConfig | None = None,
        trace_recorder: TraceRecorder | None = None,
    ) -> "NativeBioRuntime":
        compiled = graph.compile() if hasattr(graph, "compile") else graph
        native_compiled = (
            compiled
            if isinstance(compiled, NativeCompiledBioGraph)
            else NativeCompiledBioGraph.from_compiled_graph(compiled)
        )
        return cls(
            native_compiled,
            checkpointer=checkpointer,
            config=config,
            trace_recorder=trace_recorder,
        )

    def invoke(
        self,
        input_state: Any | None = None,
        *,
        context: dict[str, Any] | None = None,
        checkpoint_id: str | None = None,
    ) -> RuntimeResult:
        return super().invoke(input_state, context=context, checkpoint_id=checkpoint_id)
