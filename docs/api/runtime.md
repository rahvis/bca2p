# `bca2p.runtime`

`bca2p.runtime` provides the stable local executor and checkpoint storage surfaces.

## Main Objects

- `BioRuntime`
- `RuntimeConfig`
- `RuntimeResult`
- `StateSnapshot`
- `InMemoryCheckpointer`
- `FileCheckpointer`

## Features Implemented in Phase 4

- super-step execution
- signal queue handling
- TTL and decay application
- amplification cap enforcement through `HomeostasisPolicy`
- in-memory and file-backed checkpoints
- replay
- fork replay
