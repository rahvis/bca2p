# Migration Guide

This guide compares standard orchestration patterns with `bca2p`.

## LangGraph to `bca2p`

- Replace ad hoc state keys with channel mappings.
- Move implicit agent messaging into typed `SignalEnvelope` flows.
- Represent temporary collaboration using `ComplexSpec`.

## LangChain to `bca2p`

- Wrap subagents as receptor-aware tools.
- Attach causal metadata to tool invocations.
- Use quorum-aware escalation rather than prompt-only heuristics.
