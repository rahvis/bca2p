# `bca2p.distributed`

Experimental SDK-owned substrate for remote coordination.

## Main Objects

- `DistributedCoordinator`
- `TopologyEdge`
- `SignalLogEntry`
- `TopologyIndex`
- `SignalLog`
- `ArtifactStore`
- `MeshTransport`

## Backends

- `InMemoryTopologyIndex`
- `FileTopologyIndex`
- `InMemorySignalLog`
- `FileSignalLog`
- `InMemoryArtifactStore`
- `FileArtifactStore`
- `InMemoryMeshTransport`

## Scope

This module adds a minimal substrate for:

- topology persistence
- signal-event persistence
- artifact storage
- partition simulation
- replay after restart
