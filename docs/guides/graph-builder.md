# Graph Builder Guide

The `bca2p.graph` package is the authoring surface for bio-inspired workflows.

## Main Types

- `BioGraph`
- `BioNode`
- `SignalEmitter`
- `LastValueChannel`
- `TopicChannel`
- `AggregateChannel`
- `EphemeralChannel`
- `CompiledBioGraph`
- `ComplexLifecycleState`

## Basic Example

```python
from pydantic import BaseModel

from bca2p.core import ComplexSpec, QuorumRule, ReceptorSpec, SignalMode
from bca2p.graph import BioGraph


class ResearchPayload(BaseModel):
    query: str


def planner_handler(state, context):
    context.emitter.emit(
        mode=SignalMode.ENDOCRINE,
        recipient_scope="research.team",
        receptor="research.query",
        payload={"query": "map the patent landscape"},
    )
    return {"status": "planned"}


graph = BioGraph(metadata={"scopes": ["research.team"]})
graph.add_channel("signals", mode="topic")
graph.add_agent(
    "planner",
    planner_handler,
    scope_subscriptions=["research.team"],
    output_channel="signals",
)
graph.add_agent(
    "researcher",
    planner_handler,
    receptors=[
        ReceptorSpec.from_payload_model(
            receptor_id="research.query",
            payload_model=ResearchPayload,
            accepted_modes=[SignalMode.ENDOCRINE, SignalMode.PARACRINE],
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

compiled = graph.compile()
```

## Subscription Model

`BioNode` supports three routing-oriented subscription styles:

- receptor-bound
  - signal targets a specific `receptor_id`
- scope-bound
  - signal `recipient_scope` matches one of the node's scope patterns
- topology-bound
  - signal `policy_tags` intersect with node topology tags

## Channel Types

- `LastValueChannel`
  - keeps the latest update
- `TopicChannel`
  - stores a sequence of updates
- `AggregateChannel`
  - reduces updates into a persistent value
- `EphemeralChannel`
  - stores a temporary value until reset

## Validation Rules in `compile()`

`BioGraph.compile()` currently validates:

- duplicate agent IDs
- duplicate receptor IDs across agents
- missing channel references
- invalid quorum scopes
- orphan agents with no subscriptions, channels, receptors, or complex membership
