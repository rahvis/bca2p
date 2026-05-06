# Runtime and Checkpointing Guide

`bca2p.runtime` is the stable local execution layer built around checkpointed super-steps.

## Main Objects

- `BioRuntime`
- `RuntimeConfig`
- `StateSnapshot`
- `RuntimeResult`
- `InMemoryCheckpointer`
- `FileCheckpointer`

## Execution Model

Each invocation proceeds in repeated super-steps:

1. Plan active nodes
2. Execute active nodes against the current visible state
3. Apply channel updates and stage outgoing signals for the next step
4. Persist a checkpoint snapshot

Channel updates from a step are not visible to other nodes until the next step.

## Checkpointing

Each `StateSnapshot` stores:

- graph state
- channel values
- pending signals
- active nodes
- updated channels
- complex lifecycle states

## Example

```python
from bca2p.runtime import BioRuntime, InMemoryCheckpointer, RuntimeConfig

runtime = BioRuntime(
    compiled_graph,
    checkpointer=InMemoryCheckpointer(),
    config=RuntimeConfig(max_steps=20),
)

result = runtime.invoke({"workflow_id": "wf-1"})
history = runtime.get_state_history()
latest = runtime.get_state()
```
