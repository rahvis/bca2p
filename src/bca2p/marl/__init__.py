"""Experimental differentiable-style communication training for bca2p."""

from .models import (
    CommunicationAction,
    LearnedCommunicationPolicy,
    PolicyEvaluation,
    RewardBreakdown,
    RolloutTrace,
    RolloutTraceCollector,
    RolloutTransition,
    TrainerConfig,
    TrainingEnvironment,
    TrainingObservation,
    TrainingSummary,
)
from .trainer import CommunicationTrainer, RewardFunction, SyntheticCommunicationEnvironment

__all__ = [
    "CommunicationAction",
    "CommunicationTrainer",
    "LearnedCommunicationPolicy",
    "PolicyEvaluation",
    "RewardBreakdown",
    "RewardFunction",
    "RolloutTrace",
    "RolloutTraceCollector",
    "RolloutTransition",
    "SyntheticCommunicationEnvironment",
    "TrainerConfig",
    "TrainingEnvironment",
    "TrainingObservation",
    "TrainingSummary",
]
