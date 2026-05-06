# `bca2p.graph`

`bca2p.graph` contains the authoring layer for bio-inspired workflows.

## Main Objects

- `BioGraph`
- `BioNode`
- `BioNodeContext`
- `SignalEmitter`
- `CompiledBioGraph`
- `CompiledComplex`
- `ComplexLifecycleState`

## Channel Types

- `LastValueChannel`
- `TopicChannel`
- `AggregateChannel`
- `EphemeralChannel`

## Validation

`BioGraph.compile()` performs compile-time validation for:

- missing channel references
- duplicate receptor IDs
- invalid quorum scopes
- orphan agents

## Example

```python
from bca2p.graph import BioGraph

graph = BioGraph(metadata={"scopes": ["research.team"]})
graph.add_channel("signals", mode="topic")
```
