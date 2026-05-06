# Core API Guide

The stable `bca2p` API is built around five layers:

1. `bca2p.core`
2. `bca2p.graph`
3. `bca2p.runtime`
4. `bca2p.learning`
5. `bca2p.observability`

## Core Protocol

Use `SignalEnvelope` and `ReceptorSpec` to define typed communication contracts.

## Authoring Graphs

Use `BioGraph` and `BioNode` to declare agents, channels, complexes, and quorum rules.

## Execution

Use `BioRuntime` for stable super-step execution with checkpointing and replay.

## Adaptive Feedback

Use `CausalFeedback` and `CausalGraphStore` to attach outcome and attribution signals to prior communication steps.

## Diagnostics

Use `TraceRecorder` and the diagnostics helpers to inspect delivery, drops, quorum triggers, and homeostasis interventions.
