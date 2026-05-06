# Getting Started

This guide helps new developers evaluate the stable `bca2p` SDK path.

## Stable Entry Points

- Graph authoring: `bca2p.graph`
- Local runtime: `bca2p.runtime`
- Observability: `bca2p.observability`
- LangGraph adapter: `bca2p.integrations.langgraph`
- LangChain middleware: `bca2p.integrations.langchain`

## Reference Examples

- [LangGraph research swarm](../../examples/langgraph_research_swarm/README.md)
- [LangChain support swarm](../../examples/langchain_support_swarm/README.md)
- [Native runtime example](../../examples/native_runtime/README.md)
- [MARL training example](../../examples/marl_training/README.md)
- [Cell simulation example](../../examples/cell_simulation/README.md)
- [Distributed mesh example](../../examples/distributed_mesh/README.md)

## Benchmark Harness

Run the benchmark harness:

```bash
PYTHONPATH=src python3 examples/benchmark_harness.py
```

## What to Compare

- standard orchestration patterns
- typed signal routing
- communication overhead
- routing clarity
- replay fidelity
