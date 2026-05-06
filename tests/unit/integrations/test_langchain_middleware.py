from __future__ import annotations

import pytest

from bca2p.core import AgentProfile, HomeostasisPolicy, QuorumRule, ReceptorSpec, SignalMode
from bca2p.integrations.langchain import BioAgentMiddleware, ReceptorAwareSubagent


def billing_handler(payload: dict) -> dict:
    return {"billing_status": "resolved", "ticket": payload["ticket_id"]}


@pytest.mark.asyncio
async def test_langchain_middleware_builds_signal_aware_subagent_tools() -> None:
    middleware = BioAgentMiddleware(
        agent_id="support_orchestrator",
        homeostasis_policy=HomeostasisPolicy.default(),
        quorum_rules=[
            QuorumRule(
                rule_id="human_escalation",
                target_scope="support.local",
                threshold=0.6,
                min_participants=1,
            )
        ],
    )
    profile = AgentProfile(
        agent_id="billing_agent",
        scopes=["support.local"],
        receptors=[ReceptorSpec(receptor_id="support.billing", accepted_modes=[SignalMode.PARACRINE])],
    )
    middleware.register_subagent(ReceptorAwareSubagent(profile=profile, handler=billing_handler))
    tool = middleware.subagent_tool("billing_agent", policy_tags=["support"])

    signal, result = await tool.ainvoke_with_signal(
        recipient_scope="support.local",
        payload={"ticket_id": "t-1"},
        correlation_id="corr-1",
    )
    signal = middleware.attach_causal_metadata(signal, parent_signal_id="parent-1", correlation_id="corr-1")
    throttled = middleware.throttle_signal(signal)

    assert result["billing_status"] == "resolved"
    assert throttled.causal_parent_id == "parent-1"
    assert throttled.correlation_id == "corr-1"
    assert middleware.create_agent_kwargs()["metadata"]["bca2p"]["agent_id"] == "support_orchestrator"


def test_langchain_homeostasis_and_quorum_escalation_helpers() -> None:
    middleware = BioAgentMiddleware(
        agent_id="support_orchestrator",
        homeostasis_policy=HomeostasisPolicy(noisy_sender_threshold=1),
        quorum_rules=[
            QuorumRule(
                rule_id="human_escalation",
                target_scope="support.local",
                threshold=0.6,
                min_participants=1,
            )
        ],
    )
    assert middleware.homeostasis_allows_retry("ticket-1") is True
    middleware.record_retry("ticket-1")
    assert middleware.homeostasis_allows_retry("ticket-1") is False

    escalation = middleware.evaluate_escalation(
        target_scope="support.local",
        disagreement_ratio=0.7,
        confidence=0.2,
    )
    assert escalation.should_escalate is True
    assert escalation.matched_rule_ids == ["human_escalation"]
