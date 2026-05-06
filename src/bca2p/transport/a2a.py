"""A2A bridge helpers for translating bca2p signals and agent metadata."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from bca2p.core import AgentProfile, ArtifactRef, SignalEnvelope, SignalMode


class A2ABridge:
    """Translate between bca2p protocol objects and A2A-compatible payloads."""

    @staticmethod
    def signal_to_message(signal: SignalEnvelope) -> dict[str, Any]:
        parts: list[dict[str, Any]] = [
            {
                "kind": "data",
                "mimeType": "application/json",
                "data": deepcopy(signal.payload),
            }
        ]
        for artifact in signal.artifact_refs:
            parts.append(A2ABridge.artifact_to_part(artifact))

        return {
            "messageId": signal.signal_id,
            "role": "user",
            "parts": parts,
            "metadata": {
                "bca2p": {
                    "mode": signal.mode.value,
                    "sender": signal.sender,
                    "recipient_scope": signal.recipient_scope,
                    "receptor": signal.receptor,
                    "priority": signal.priority.value,
                    "ttl": signal.ttl,
                    "decay": signal.decay,
                    "amplification": signal.amplification,
                    "confidence": signal.confidence,
                    "causal_parent_id": signal.causal_parent_id,
                    "correlation_id": signal.correlation_id,
                    "trace_path": list(signal.trace_path),
                    "trust_level": signal.trust_level.value if signal.trust_level is not None else None,
                    "policy_tags": list(signal.policy_tags),
                }
            },
        }

    @staticmethod
    def signal_to_send_request(signal: SignalEnvelope, *, blocking: bool = True) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": signal.signal_id,
            "method": "message/send",
            "params": {
                "message": A2ABridge.signal_to_message(signal),
                "configuration": {"blocking": blocking},
            },
        }

    @staticmethod
    def agent_profile_to_agent_card(profile: AgentProfile, *, url: str) -> dict[str, Any]:
        return {
            "name": profile.display_name or profile.agent_id,
            "description": profile.description or "",
            "version": profile.version,
            "url": url,
            "capabilities": {
                "streaming": True,
                "pushNotifications": False,
            },
            "skills": [
                {
                    "id": receptor.receptor_id,
                    "name": receptor.receptor_id,
                    "description": receptor.payload_schema or receptor.receptor_id,
                }
                for receptor in profile.receptors
            ],
            "metadata": {
                "bca2p": {
                    "agent_id": profile.agent_id,
                    "scopes": list(profile.scopes),
                    "trust_level": profile.trust_level.value,
                    "receptors": [receptor.to_dict() for receptor in profile.receptors],
                }
            },
        }

    @staticmethod
    def artifact_to_part(artifact: ArtifactRef) -> dict[str, Any]:
        return {
            "kind": "file",
            "file": {
                "name": artifact.artifact_id,
                "uri": artifact.uri,
                "mimeType": artifact.media_type,
                "metadata": {
                    "checksum": artifact.checksum,
                    **artifact.metadata,
                },
            },
        }

    @staticmethod
    def message_to_signal(message: dict[str, Any]) -> SignalEnvelope:
        metadata = deepcopy(message.get("metadata", {}).get("bca2p", {}))
        parts = message.get("parts", [])
        payload: dict[str, Any] = {}
        artifact_refs: list[ArtifactRef] = []
        for part in parts:
            if part.get("kind") == "data":
                payload.update(part.get("data", {}))
            elif part.get("kind") == "file":
                file_info = part.get("file", {})
                artifact_refs.append(
                    ArtifactRef(
                        artifact_id=file_info.get("name", "artifact"),
                        uri=file_info.get("uri", ""),
                        media_type=file_info.get("mimeType"),
                        metadata=deepcopy(file_info.get("metadata", {})),
                    )
                )
        return SignalEnvelope(
            signal_id=message.get("messageId", "remote-signal"),
            mode=SignalMode(metadata.get("mode", SignalMode.PARACRINE.value)),
            sender=metadata.get("sender", "remote-agent"),
            recipient_scope=metadata.get("recipient_scope", "remote.scope"),
            receptor=metadata.get("receptor"),
            payload=payload,
            ttl=metadata.get("ttl"),
            decay=metadata.get("decay"),
            amplification=metadata.get("amplification", 1.0),
            confidence=metadata.get("confidence"),
            causal_parent_id=metadata.get("causal_parent_id"),
            correlation_id=metadata.get("correlation_id"),
            trace_path=metadata.get("trace_path", ["remote-agent"]),
            policy_tags=metadata.get("policy_tags", []),
            artifact_refs=artifact_refs,
        )

    @staticmethod
    def response_to_signal(response: dict[str, Any]) -> SignalEnvelope:
        result = response.get("result", {})
        if "message" in result:
            return A2ABridge.message_to_signal(result["message"])
        if "messages" in result and result["messages"]:
            return A2ABridge.message_to_signal(result["messages"][-1])
        raise ValueError("A2A response does not contain a message payload")
