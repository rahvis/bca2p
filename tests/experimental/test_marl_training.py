from __future__ import annotations

from pathlib import Path

from examples.marl_training.app import run_training_example

from bca2p.marl import CommunicationTrainer, SyntheticCommunicationEnvironment, TrainerConfig


def test_marl_training_improves_over_baseline() -> None:
    trainer = CommunicationTrainer(config=TrainerConfig(episodes=30, epsilon=0.2, seed=5))
    summary = trainer.train(SyntheticCommunicationEnvironment())

    assert summary.evaluation.average_reward > summary.baseline_evaluation.average_reward
    assert summary.evaluation.success_rate >= summary.baseline_evaluation.success_rate


def test_marl_example_exports_policy() -> None:
    result = run_training_example()

    assert result["trained_average_reward"] > result["baseline_average_reward"]
    assert Path(result["policy_path"]).exists()
