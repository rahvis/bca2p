# `bca2p.marl`

Experimental communication-policy learning layer.

## Main Objects

- `CommunicationAction`
- `TrainingObservation`
- `RewardBreakdown`
- `RolloutTransition`
- `RolloutTrace`
- `RolloutTraceCollector`
- `LearnedCommunicationPolicy`
- `TrainerConfig`
- `PolicyEvaluation`
- `TrainingSummary`
- `CommunicationTrainer`
- `RewardFunction`
- `SyntheticCommunicationEnvironment`

## Scope

This module provides a centralized-training / decentralized-execution baseline for:

- route choice
- amplification tuning
- quorum threshold selection
- complex membership selection

The implementation is intentionally lightweight and deterministic enough for repeatable tests and example runs.
