"""Transport interfaces and implementations for bca2p."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Protocol

from bca2p.core import AgentProfile, SignalEnvelope
from bca2p.registry import AgentRegistry

from .a2a import A2ABridge

SignalHandler = Callable[[SignalEnvelope], SignalEnvelope | list[SignalEnvelope] | Awaitable[SignalEnvelope | list[SignalEnvelope]]]


class RemoteTransport(Protocol):
    """Protocol for remote signal transports."""

    async def send(self, signal: SignalEnvelope, *, endpoint: str) -> SignalEnvelope:
        """Send a signal to a remote endpoint and normalize the response."""


@dataclass
class LocalTransport:
    """In-process transport with handler registration and registry-backed discovery."""

    registry: AgentRegistry
    handlers: dict[str, SignalHandler] = field(default_factory=dict)

    def register_handler(self, agent_id: str, handler: SignalHandler) -> None:
        self.handlers[agent_id] = handler

    async def send(self, signal: SignalEnvelope) -> list[SignalEnvelope]:
        candidate_profiles = self.registry.find_by_receptor(signal.receptor) if signal.receptor else []
        if not candidate_profiles:
            candidate_profiles = self.registry.find_by_scope(signal.recipient_scope)
        responses: list[SignalEnvelope] = []
        for profile in candidate_profiles:
            handler = self.handlers.get(profile.agent_id)
            if handler is None:
                continue
            result = handler(signal)
            if hasattr(result, "__await__"):
                result = await result  # type: ignore[assignment]
            if isinstance(result, list):
                responses.extend(result)
            else:
                responses.append(result)
        return responses


class HttpA2ATransport:
    """HTTP/SSE transport adapter for A2A-compatible servers."""

    def __init__(self) -> None:
        self._httpx = None
        try:
            import httpx  # type: ignore
        except Exception:  # noqa: BLE001
            httpx = None
        self._httpx = httpx

    async def send(self, signal: SignalEnvelope, *, endpoint: str) -> SignalEnvelope:
        if self._httpx is None:
            raise RuntimeError("httpx is not available in the current environment")
        payload = A2ABridge.signal_to_send_request(signal)
        async with self._httpx.AsyncClient() as client:
            response = await client.post(endpoint, json=payload, headers={"content-type": "application/json"})
            response.raise_for_status()
            return A2ABridge.response_to_signal(response.json())


@dataclass
class RemoteSignalNormalizer:
    """Normalizes remote responses back into local signal traces."""

    def from_a2a_response(self, response: dict[str, Any]) -> SignalEnvelope:
        return A2ABridge.response_to_signal(response)
