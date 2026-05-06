from __future__ import annotations

from dataclasses import dataclass
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for _path in (ROOT, SRC):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)

from bca2p.core import AgentProfile, HomeostasisPolicy, QuorumRule, ReceptorSpec, SignalMode
from bca2p.integrations.langchain import BioAgentMiddleware, ReceptorAwareSubagent


def billing_handler(payload: dict[str, Any]) -> dict[str, Any]:
    return {"billing_status": "resolved", "ticket": payload["ticket_id"]}


def troubleshooting_handler(payload: dict[str, Any]) -> dict[str, Any]:
    return {"troubleshooting_status": "investigating", "ticket": payload["ticket_id"]}


def build_middleware() -> BioAgentMiddleware:
    billing_profile = AgentProfile(
        agent_id="billing_agent",
        scopes=["support.local"],
        receptors=[
            ReceptorSpec(
                receptor_id="support.billing",
                accepted_modes=[SignalMode.PARACRINE],
            )
        ],
    )
    troubleshooting_profile = AgentProfile(
        agent_id="troubleshooting_agent",
        scopes=["support.local"],
        receptors=[
            ReceptorSpec(
                receptor_id="support.troubleshooting",
                accepted_modes=[SignalMode.PARACRINE],
            )
        ],
    )
    middleware = BioAgentMiddleware(
        agent_id="support_orchestrator",
        homeostasis_policy=HomeostasisPolicy.default(),
        quorum_rules=[
            QuorumRule(
                rule_id="human_escalation",
                target_scope="support.local",
                threshold=0.6,
                min_participants=1,
                action="escalate_to_human",
            )
        ],
    )
    middleware.register_subagent(ReceptorAwareSubagent(profile=billing_profile, handler=billing_handler))
    middleware.register_subagent(
        ReceptorAwareSubagent(profile=troubleshooting_profile, handler=troubleshooting_handler)
    )
    return middleware


@dataclass
class SupportRunResult:
    billing_signal: dict[str, Any]
    billing_result: dict[str, Any]
    troubleshooting_signal: dict[str, Any]
    troubleshooting_result: dict[str, Any]
    escalation: dict[str, Any]


async def run_support_swarm(ticket_id: str) -> SupportRunResult:
    middleware = build_middleware()
    billing_tool = middleware.subagent_tool("billing_agent", policy_tags=["support", "billing"])
    troubleshooting_tool = middleware.subagent_tool(
        "troubleshooting_agent",
        policy_tags=["support", "troubleshooting"],
    )

    billing_signal, billing_result = await billing_tool.ainvoke_with_signal(
        recipient_scope="support.local",
        payload={"ticket_id": ticket_id},
        correlation_id=f"ticket:{ticket_id}",
    )
    troubleshooting_signal, troubleshooting_result = await troubleshooting_tool.ainvoke_with_signal(
        recipient_scope="support.local",
        payload={"ticket_id": ticket_id},
        correlation_id=f"ticket:{ticket_id}",
    )

    escalation = middleware.evaluate_escalation(
        target_scope="support.local",
        disagreement_ratio=0.65,
        confidence=0.3,
    )

    return SupportRunResult(
        billing_signal=billing_signal.to_dict(),
        billing_result=billing_result,
        troubleshooting_signal=troubleshooting_signal.to_dict(),
        troubleshooting_result=troubleshooting_result,
        escalation={
            "should_escalate": escalation.should_escalate,
            "reason": escalation.reason,
            "matched_rule_ids": escalation.matched_rule_ids,
        },
    )


if __name__ == "__main__":
    import asyncio

    print(asyncio.run(run_support_swarm("ticket-1001")))
