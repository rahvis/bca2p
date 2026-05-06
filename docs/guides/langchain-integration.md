# LangChain Integration Guide

`bca2p.integrations.langchain` provides a framework-agnostic surface aligned with common LangChain agent patterns.

## Main Entry Points

- `BioAgentMiddleware`
- `ReceptorAwareSubagent`
- `BioSubagentTool`
- `EscalationDecision`

## Typical Flow

1. Register receptor-aware subagents.
2. Wrap them as bio-aware tools.
3. Attach causal metadata to each routed subagent call.
4. Apply homeostasis-aware retry and throttle rules.
5. Escalate with quorum-aware rules instead of prompt-only heuristics.

## Reference Example

See [examples/langchain_support_swarm/README.md](../../examples/langchain_support_swarm/README.md).
