"""Experimental centralized-training utilities for communication policies."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

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
    TrainingSummary,
)


@dataclass(slots=True)
class RewardFunction:
    """Composable reward helper for communication-learning benchmarks."""

    task_weight: float = 1.0
    communication_cost_weight: float = 1.0
    stability_penalty_weight: float = 1.0
    failure_recovery_bonus_weight: float = 1.0

    def build(
        self,
        *,
        task_reward: float,
        communication_cost: float,
        stability_penalty: float,
        failure_recovery_bonus: float,
    ) -> RewardBreakdown:
        return RewardBreakdown(
            task_reward=task_reward * self.task_weight,
            communication_cost=communication_cost * self.communication_cost_weight,
            stability_penalty=stability_penalty * self.stability_penalty_weight,
            failure_recovery_bonus=failure_recovery_bonus * self.failure_recovery_bonus_weight,
        )


@dataclass(slots=True)
class CommunicationTrainer:
    """Centralized trainer with decentralized execution policy outputs."""

    config: TrainerConfig = field(default_factory=TrainerConfig)
    reward_function: RewardFunction = field(default_factory=RewardFunction)
    rollout_collector: RolloutTraceCollector = field(default_factory=RolloutTraceCollector)

    def train(self, environment: TrainingEnvironment) -> TrainingSummary:
        rng = random.Random(self.config.seed)
        policy = LearnedCommunicationPolicy()
        traces: list[RolloutTrace] = []

        for episode_index in range(self.config.episodes):
            observation = environment.reset()
            transitions: list[RolloutTransition] = []
            total_steps = 0
            while True:
                action = policy.select_action(observation, epsilon=self.config.epsilon, rng=rng)
                next_observation, reward, done, metadata = environment.step(action)
                total_steps += 1
                transitions.append(
                    RolloutTransition(
                        state_key=observation.state_key,
                        action=action,
                        reward=reward,
                        next_state_key=next_observation.state_key,
                        done=done,
                        metadata=dict(metadata),
                    )
                )
                self._update_value(
                    policy,
                    observation.state_key,
                    action,
                    reward,
                    next_observation.state_key,
                )
                observation = next_observation
                if done:
                    trace = RolloutTrace(
                        episode_id=f"episode-{episode_index:04d}",
                        agent_id=observation.agent_id,
                        transitions=transitions,
                        emitted_signals=metadata.get("emitted_signals", total_steps),
                        delivered_signals=metadata.get("delivered_signals", total_steps),
                        dropped_signals=metadata.get("dropped_signals", 0),
                        homeostasis_interventions=metadata.get("homeostasis_interventions", 0),
                        metadata={
                            "success": metadata.get("success", reward.total > 0),
                            "steps": total_steps,
                        },
                    )
                    traces.append(trace)
                    break

        evaluation = self.evaluate(environment, policy, episodes=max(10, self.config.episodes // 5))
        baseline_evaluation = self.evaluate_baseline(
            environment,
            episodes=max(10, self.config.episodes // 5),
        )
        return TrainingSummary(
            policy=policy,
            traces=traces,
            evaluation=evaluation,
            baseline_evaluation=baseline_evaluation,
            metadata={"episodes": self.config.episodes},
        )

    def evaluate(
        self,
        environment: TrainingEnvironment,
        policy: LearnedCommunicationPolicy,
        *,
        episodes: int = 10,
    ) -> PolicyEvaluation:
        rewards: list[float] = []
        successes = 0
        for _ in range(episodes):
            observation = environment.reset()
            while True:
                action = policy.select_action(observation, epsilon=0.0)
                observation, reward, done, metadata = environment.step(action)
                if done:
                    rewards.append(reward.total)
                    successes += 1 if metadata.get("success", reward.total > 0) else 0
                    break
        return PolicyEvaluation(
            average_reward=sum(rewards) / max(len(rewards), 1),
            success_rate=successes / max(episodes, 1),
            episode_count=episodes,
        )

    def evaluate_baseline(
        self,
        environment: TrainingEnvironment,
        *,
        episodes: int = 10,
    ) -> PolicyEvaluation:
        rewards: list[float] = []
        successes = 0
        for _ in range(episodes):
            observation = environment.reset()
            while True:
                action = environment.baseline_action(observation)
                observation, reward, done, metadata = environment.step(action)
                if done:
                    rewards.append(reward.total)
                    successes += 1 if metadata.get("success", reward.total > 0) else 0
                    break
        return PolicyEvaluation(
            average_reward=sum(rewards) / max(len(rewards), 1),
            success_rate=successes / max(episodes, 1),
            episode_count=episodes,
        )

    def _update_value(
        self,
        policy: LearnedCommunicationPolicy,
        state_key: str,
        action: CommunicationAction,
        reward: RewardBreakdown,
        next_state_key: str,
    ) -> None:
        current = policy.score(state_key, action)
        next_values = policy.value_table.get(next_state_key, {})
        next_best = max(next_values.values()) if next_values else 0.0
        updated = current + self.config.learning_rate * (
            reward.total + (self.config.discount * next_best) - current
        )
        policy.update(state_key, action, updated)


@dataclass(slots=True)
class SyntheticCommunicationEnvironment:
    """Deterministic benchmark environment for route/amplification/quorum learning."""

    agent_id: str = "planner"
    reward_function: RewardFunction = field(default_factory=RewardFunction)
    scenario_cycle: tuple[str, ...] = ("billing", "research", "escalation")
    _episode: int = 0
    _step: int = 0
    _current_scenario: str = "billing"

    def reset(self) -> Any:
        self._current_scenario = self.scenario_cycle[self._episode % len(self.scenario_cycle)]
        self._episode += 1
        self._step = 0
        return self._observation_for(self._current_scenario)

    def step(
        self,
        action: CommunicationAction,
    ) -> tuple[Any, RewardBreakdown, bool, dict[str, Any]]:
        self._step += 1
        score = self._score_action(self._current_scenario, action)
        reward = self.reward_function.build(
            task_reward=score["task_reward"],
            communication_cost=score["communication_cost"],
            stability_penalty=score["stability_penalty"],
            failure_recovery_bonus=score["failure_recovery_bonus"],
        )
        done = True
        next_observation = self._observation_for(f"terminal:{self._current_scenario}")
        return next_observation, reward, done, {
            "success": reward.total > 0,
            "scenario": self._current_scenario,
            "emitted_signals": 1,
            "delivered_signals": 1 if reward.total > 0 else 0,
            "dropped_signals": 0 if reward.total > 0 else 1,
            "homeostasis_interventions": 1 if action.amplification_level > 2.0 else 0,
        }

    def baseline_action(self, observation: Any) -> CommunicationAction:
        return observation.candidate_actions[0]

    def _observation_for(self, state_key: str) -> Any:
        return TrainingObservation(
            agent_id=self.agent_id,
            state_key=state_key,
            candidate_actions=self._candidate_actions(state_key),
            features={"step": float(self._step)},
            metadata={"scenario": state_key},
        )

    def _candidate_actions(self, state_key: str) -> list[CommunicationAction]:
        scenario = state_key.removeprefix("terminal:")
        if scenario == "billing":
            return [
                CommunicationAction(
                    route_choice="generalist",
                    amplification_level=2.5,
                    quorum_threshold=0.7,
                    complex_members=("planner",),
                ),
                CommunicationAction(
                    route_choice="billing_agent",
                    amplification_level=1.0,
                    quorum_threshold=0.5,
                    complex_members=("planner", "billing_agent"),
                ),
            ]
        if scenario == "research":
            return [
                CommunicationAction(
                    route_choice="critic",
                    amplification_level=1.0,
                    quorum_threshold=0.8,
                    complex_members=("planner", "critic"),
                ),
                CommunicationAction(
                    route_choice="researcher",
                    amplification_level=1.5,
                    quorum_threshold=0.4,
                    complex_members=("planner", "researcher", "critic"),
                ),
            ]
        return [
            CommunicationAction(
                route_choice="support_agent",
                amplification_level=1.0,
                quorum_threshold=0.9,
                complex_members=("support_agent",),
            ),
            CommunicationAction(
                route_choice="escalation_agent",
                amplification_level=1.2,
                quorum_threshold=0.35,
                complex_members=("planner", "escalation_agent", "human_review"),
            ),
        ]

    def _score_action(self, scenario: str, action: CommunicationAction) -> dict[str, float]:
        if scenario == "billing":
            success = action.route_choice == "billing_agent"
            stable = action.amplification_level <= 1.5
        elif scenario == "research":
            success = action.route_choice == "researcher"
            stable = action.quorum_threshold <= 0.5 and len(action.complex_members) >= 3
        else:
            success = action.route_choice == "escalation_agent"
            stable = action.quorum_threshold <= 0.4 and "human_review" in action.complex_members

        communication_cost = 0.15 * max(action.amplification_level, 1.0)
        communication_cost += 0.05 * max(len(action.complex_members) - 1, 0)
        stability_penalty = 0.0 if stable else 0.45
        task_reward = 1.35 if success else 0.25
        failure_recovery_bonus = 0.35 if scenario == "escalation" and success else 0.0
        return {
            "task_reward": task_reward,
            "communication_cost": communication_cost,
            "stability_penalty": stability_penalty,
            "failure_recovery_bonus": failure_recovery_bonus,
        }
