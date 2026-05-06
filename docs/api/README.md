# API Docs Index

This section will host API-oriented documentation for:

- `bca2p.core`
- `bca2p.graph`
- `bca2p.runtime`
- `bca2p.learning`
- `bca2p.transport`
- `bca2p.registry`
- `bca2p.observability`
- integrations and experimental modules

## Implemented in Phase 2

The first concrete API surface now exists in `bca2p.core`.

Core protocol objects:

- `SignalMode`
- `PriorityLevel`
- `TrustLevel`
- `FeedbackType`
- `TopologyStrategy`
- `SignalEnvelope`
- `ReceptorSpec`
- `ComplexSpec`
- `QuorumRule`
- `HomeostasisPolicy`
- `TopologyPolicy`
- `ContributionFactor`
- `CausalFeedback`
- `ArtifactRef`
- `AgentProfile`

Core support utilities:

- `ProtocolModel`
- `CORE_SCHEMA_VERSION`
- `SCHEMA_METADATA_KEY`

Core exceptions:

- `BCA2PError`
- `SchemaVersionError`
- `SignalValidationError`
- `RoutingError`
- `TrustPolicyError`

Phase 2 status:

- versioned core schema models implemented
- schema serialization helpers implemented
- unit tests added for validation and round-tripping

## Implemented in Phase 3

The graph authoring layer now exists in `bca2p.graph`.

Graph-layer objects:

- `BioGraph`
- `BioNode`
- `BioNodeContext`
- `SignalEmitter`
- `CompiledBioGraph`
- `CompiledComplex`
- `ComplexLifecycleState`

Channel objects:

- `LastValueChannel`
- `TopicChannel`
- `AggregateChannel`
- `EphemeralChannel`

Graph exceptions:

- `GraphValidationError`

## Implemented in Phase 4

The stable execution layer now exists in `bca2p.runtime`.

Runtime objects:

- `BioRuntime`
- `RuntimeConfig`
- `RuntimeResult`
- `StateSnapshot`

Checkpointing objects:

- `InMemoryCheckpointer`
- `FileCheckpointer`

Runtime exceptions:

- `RuntimeExecutionError`
- `ReplayError`

## Implemented in Phase 5

The causal learning layer now exists in `bca2p.learning`.

Learning objects:

- `CausalGraphStore`
- `CausalSignalEdge`
- `CausalDecisionNode`
- `CausalOutcomeNode`
- `ContributionSummary`
- `CounterfactualResult`
- `PolicyRefinementProposal`

Learning exceptions:

- `CausalGraphError`
- `CounterfactualError`

## Implemented in Phase 6

The observability layer now exists in `bca2p.observability`.

Observability objects:

- `TraceRecorder`
- `RuntimeEvent`
- `RuntimeEventType`
- `TopologySnapshot`
- `ReplayEventBundle`
- `VisualizationGraph`

Diagnostics:

- `detect_bottlenecks(...)`
- `noisy_sender_report(...)`
- `dormant_receptor_report(...)`
- `amplification_storm_report(...)`

## Implemented in Phase 7

The discovery and transport layers now exist in `bca2p.registry` and `bca2p.transport`.

Registry objects:

- `AgentRegistry`
- `RegistryStore`
- `InMemoryRegistryStore`
- `FileRegistryStore`

Transport objects:

- `LocalTransport`
- `RemoteTransport`
- `HttpA2ATransport`
- `RemoteSignalNormalizer`
- `A2ABridge`

## Implemented in Phase 8

The LangGraph adapter now exists in `bca2p.integrations.langgraph`.

LangGraph integration objects:

- `LangGraphAdapter`
- `LangGraphChannelMapping`
- `LangGraphComplexBranch`

## Implemented in Phase 9

The LangChain middleware layer now exists in `bca2p.integrations.langchain`.

LangChain integration objects:

- `BioAgentMiddleware`
- `ReceptorAwareSubagent`
- `BioSubagentTool`
- `EscalationDecision`

## Implemented in Phase 10

Stable examples and the benchmark harness now exist under `examples/`.

Included:

- LangGraph research swarm
- LangChain support swarm
- standard comparison flows
- benchmark harness

## Implemented in Phase 11

The first-party native runtime now exists in `bca2p.native`.

Native runtime objects:

- `NativeCompiledBioGraph`
- `NativeBioRuntime`

## Implemented in Phase 12

The experimental MARL module now exists in `bca2p.marl`.

MARL objects:

- `CommunicationAction`
- `TrainingObservation`
- `RewardBreakdown`
- `RolloutTrace`
- `RolloutTraceCollector`
- `LearnedCommunicationPolicy`
- `CommunicationTrainer`
- `SyntheticCommunicationEnvironment`

## Implemented in Phase 13

The experimental simulation module now exists in `bca2p.sim`.

Simulation objects:

- `CellWorld`
- `Cell`
- `Ligand`
- `Receptor`
- `DiffusionField`
- `CascadeModel`

## Implemented in Phase 14

The experimental distributed substrate now exists in `bca2p.distributed`.

Distributed objects:

- `DistributedCoordinator`
- `TopologyEdge`
- `SignalLogEntry`
- `TopologyIndex`
- `SignalLog`
- `ArtifactStore`
- `MeshTransport`
