from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for _path in (ROOT, SRC):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)

from bca2p.marl import CommunicationTrainer, SyntheticCommunicationEnvironment, TrainerConfig


def run_training_example() -> dict:
    trainer = CommunicationTrainer(config=TrainerConfig(episodes=36, epsilon=0.2, seed=11))
    environment = SyntheticCommunicationEnvironment()
    summary = trainer.train(environment)
    policy_path = ROOT / "examples" / "marl_training" / "artifacts" / "policy.json"
    summary.policy.export_json(policy_path)
    return {
        "baseline_average_reward": summary.baseline_evaluation.average_reward,
        "trained_average_reward": summary.evaluation.average_reward,
        "baseline_success_rate": summary.baseline_evaluation.success_rate,
        "trained_success_rate": summary.evaluation.success_rate,
        "episodes": len(summary.traces),
        "policy_path": str(policy_path),
    }


if __name__ == "__main__":
    print(run_training_example())
