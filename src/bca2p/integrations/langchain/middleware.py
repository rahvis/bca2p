"""LangChain-oriented middleware and wrappers for bca2p."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from bca2p.core import AgentProfile, HomeostasisPolicy, QuorumRule, SignalEnvelope, SignalMode
from bca2p.learning import CausalGraphStore


SubagentCallable = Callable[[dict[str, Any]], dict[str, Any] | Awaitable[dict[str, Any]]]


@dataclass(slots=True)
class BioSubagentTool:
    """A receptor-aware tool wrapper around a subagent callable."""

    name: str
    receptor_id: str
    subagent: SubagentCallable
    sender_id: str
    policy_tags: list[str] = field(default_factory=list)

    async def ainvoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.subagent(payload)
        if hasattr(result, "__await__"):
            return await result  # type: ignore[return-value]
        return result  # type: ignore[return-value]

    def build_signal(
        self,
        *,
        recipient_scope: str,
        payload: dict[str, Any],
        signal_id: str | None = None,
        correlation_id: str | None = None,
    ) -> SignalEnvelope:
        return SignalEnvelope(
            signal_id=signal_id or f"{self.sender_id}:{self.name}",
            mode=SignalMode.PARACRINE,
            sender=self.sender_id,
            recipient_scope=recipient_scope,
            receptor=self.receptor_id,
            payload=payload,
            correlation_id=correlation_id,
            trace_path=[self.sender_id],
            policy_tags=list(self.policy_tags),
        )

    async def ainvoke_with_signal(
        self,
        *,
        recipient_scope: str,
        payload: dict[str, Any],
        signal_id: str | None = None,
        correlation_id: str | None = None,
    ) -> tuple[SignalEnvelope, dict[str, Any]]:
        signal = self.build_signal(
            recipient_scope=recipient_scope,
            payload=payload,
            signal_id=signal_id,
            correlation_id=correlation_id,
        )
        result = await self.ainvoke(payload)
        return signal, result


@dataclass(slots=True)
class ReceptorAwareSubagent:
    """Typed subagent registration record used by LangChain middleware."""

    profile: AgentProfile
    handler: SubagentCallable

    def as_tool(self, *, sender_id: str, policy_tags: list[str] | None = None) -> BioSubagentTool:
        receptor_id = self.profile.receptors[0].receptor_id if self.profile.receptors else self.profile.agent_id
        return BioSubagentTool(
            name=self.profile.agent_id,
            receptor_id=receptor_id,
            subagent=self.handler,
            sender_id=sender_id,
            policy_tags=policy_tags or [],
        )


@dataclass(slots=True)
class EscalationDecision:
    """Structured quorum-based escalation decision."""

    should_escalate: bool
    reason: str
    matched_rule_ids: list[str] = field(default_factory=list)


@dataclass
class BioAgentMiddleware:
    """Framework-agnostic middleware that mirrors LangChain agent middleware concerns."""

    agent_id: str
    homeostasis_policy: HomeostasisPolicy | None = None
    quorum_rules: list[QuorumRule] = field(default_factory=list)
    causal_store: CausalGraphStore | None = None
    subagents: dict[str, ReceptorAwareSubagent] = field(default_factory=dict)
    retry_counters: dict[str, int] = field(default_factory=dict)

    def register_subagent(self, subagent: ReceptorAwareSubagent) -> ReceptorAwareSubagent:
        self.subagents[subagent.profile.agent_id] = subagent
        return subagent

    def subagent_tool(self, agent_id: str, *, policy_tags: list[str] | None = None) -> BioSubagentTool:
        subagent = self.subagents[agent_id]
        return subagent.as_tool(sender_id=self.agent_id, policy_tags=policy_tags)

    def build_signal_for_tool(
        self,
        *,
        agent_id: str,
        recipient_scope: str,
        payload: dict[str, Any],
        correlation_id: str | None = None,
    ) -> SignalEnvelope:
        return self.subagent_tool(agent_id).build_signal(
            recipient_scope=recipient_scope,
            payload=payload,
            correlation_id=correlation_id,
        )

    def attach_causal_metadata(
        self,
        signal: SignalEnvelope,
        *,
        parent_signal_id: str | None,
        correlation_id: str | None,
    ) -> SignalEnvelope:
        return signal.model_copy(
            update={
                "causal_parent_id": parent_signal_id,
                "correlation_id": correlation_id,
                "trace_path": list(signal.trace_path) + [self.agent_id],
            }
        )

    def homeostasis_allows_retry(self, operation_key: str) -> bool:
        limit = self.homeostasis_policy.noisy_sender_threshold if self.homeostasis_policy else 1_000_000
        count = self.retry_counters.get(operation_key, 0)
        return count < limit

    def record_retry(self, operation_key: str) -> None:
        self.retry_counters[operation_key] = self.retry_counters.get(operation_key, 0) + 1

    def throttle_signal(self, signal: SignalEnvelope) -> SignalEnvelope:
        if self.homeostasis_policy is None:
            return signal
        return signal.model_copy(
            update={
                "amplification": min(signal.amplification, self.homeostasis_policy.max_amplification),
            }
        )

    def evaluate_escalation(
        self,
        *,
        target_scope: str,
        disagreement_ratio: float,
        confidence: float,
    ) -> EscalationDecision:
        matched_rule_ids: list[str] = []
        for rule in self.quorum_rules:
            if rule.target_scope != target_scope:
                continue
            if disagreement_ratio >= rule.threshold and confidence <= (1.0 - rule.threshold):
                matched_rule_ids.append(rule.rule_id)

        if matched_rule_ids:
            return EscalationDecision(
                should_escalate=True,
                reason="quorum rules matched disagreement/confidence thresholds",
                matched_rule_ids=matched_rule_ids,
            )
        return EscalationDecision(
            should_escalate=False,
            reason="quorum conditions not met",
            matched_rule_ids=[],
        )

    def create_agent_kwargs(self) -> dict[str, Any]:
        """Return a metadata bundle suitable for optional LangChain integration."""
        return {
            "metadata": {
                "bca2p": {
                    "agent_id": self.agent_id,
                    "quorum_rules": [rule.to_dict() for rule in self.quorum_rules],
                    "homeostasis_policy": self.homeostasis_policy.to_dict() if self.homeostasis_policy else None,
                }
            }
        }
