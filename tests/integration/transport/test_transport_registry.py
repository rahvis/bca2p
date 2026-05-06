from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import BaseModel

from bca2p.core import AgentProfile, ReceptorSpec, SignalEnvelope, SignalMode
from bca2p.registry import AgentRegistry, FileRegistryStore, InMemoryRegistryStore
from bca2p.transport import A2ABridge, HttpA2ATransport, LocalTransport, RemoteSignalNormalizer


class ResearchPayload(BaseModel):
    query: str


def test_registry_store_and_catalog_support_lookup() -> None:
    registry = AgentRegistry(InMemoryRegistryStore())
    profile = AgentProfile(
        agent_id="researcher",
        scopes=["research.team"],
        receptors=[
            ReceptorSpec.from_payload_model(
                receptor_id="research.query",
                payload_model=ResearchPayload,
                accepted_modes=[SignalMode.PARACRINE],
            )
        ],
    )
    registry.register(profile)

    assert registry.get("researcher") == profile
    assert registry.find_by_scope("research.team") == [profile]
    assert registry.find_by_receptor("research.query") == [profile]
    assert registry.receptor_catalog()["researcher"] == ["research.query"]


def test_file_registry_store_round_trips_profiles() -> None:
    with TemporaryDirectory() as temp_dir:
        store = FileRegistryStore(Path(temp_dir))
        profile = AgentProfile(agent_id="planner", scopes=["research.team"])
        store.save(profile)
        loaded = store.get("planner")
        assert loaded == profile
        assert store.list() == [profile]


async def echo_handler(signal: SignalEnvelope) -> SignalEnvelope:
    return SignalEnvelope(
        signal_id=f"{signal.signal_id}:response",
        mode=SignalMode.PARACRINE,
        sender="researcher",
        recipient_scope=signal.recipient_scope,
        receptor=signal.receptor,
        payload={"received_query": signal.payload["query"]},
        trace_path=["researcher"],
    )


import pytest


@pytest.mark.asyncio
async def test_local_transport_routes_signal_through_registry() -> None:
    registry = AgentRegistry(InMemoryRegistryStore())
    profile = AgentProfile(
        agent_id="researcher",
        scopes=["research.team"],
        receptors=[
            ReceptorSpec.from_payload_model(
                receptor_id="research.query",
                payload_model=ResearchPayload,
                accepted_modes=[SignalMode.PARACRINE],
            )
        ],
    )
    registry.register(profile)

    transport = LocalTransport(registry=registry)
    transport.register_handler("researcher", echo_handler)
    signal = SignalEnvelope(
        signal_id="sig-1",
        mode=SignalMode.PARACRINE,
        sender="planner",
        recipient_scope="research.team",
        receptor="research.query",
        payload={"query": "map patents"},
        trace_path=["planner"],
    )

    responses = await transport.send(signal)
    assert len(responses) == 1
    assert responses[0].payload["received_query"] == "map patents"


def test_a2a_bridge_maps_signals_agent_cards_and_responses() -> None:
    signal = SignalEnvelope(
        signal_id="sig-1",
        mode=SignalMode.PARACRINE,
        sender="planner",
        recipient_scope="research.team",
        receptor="research.query",
        payload={"query": "map patents"},
        trace_path=["planner"],
    )
    request = A2ABridge.signal_to_send_request(signal)
    assert request["method"] == "message/send"
    assert request["params"]["message"]["metadata"]["bca2p"]["mode"] == "paracrine"

    profile = AgentProfile(agent_id="researcher", scopes=["research.team"])
    agent_card = A2ABridge.agent_profile_to_agent_card(profile, url="https://example.com/a2a")
    assert agent_card["url"] == "https://example.com/a2a"
    assert agent_card["metadata"]["bca2p"]["agent_id"] == "researcher"

    response = {
        "result": {
            "message": request["params"]["message"],
        }
    }
    normalized = RemoteSignalNormalizer().from_a2a_response(response)
    assert normalized.signal_id == "sig-1"
    assert normalized.payload["query"] == "map patents"


@pytest.mark.asyncio
async def test_http_a2a_transport_normalizes_remote_response() -> None:
    signal = SignalEnvelope(
        signal_id="sig-remote",
        mode=SignalMode.PARACRINE,
        sender="planner",
        recipient_scope="research.team",
        receptor="research.query",
        payload={"query": "map patents"},
        trace_path=["planner"],
    )

    request_payload = A2ABridge.signal_to_send_request(signal)
    response_payload = {"result": {"message": request_payload["params"]["message"]}}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return response_payload

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, endpoint, json, headers):
            assert endpoint == "https://example.com/a2a"
            assert json["method"] == "message/send"
            assert headers["content-type"] == "application/json"
            return FakeResponse()

    class FakeHttpx:
        AsyncClient = FakeAsyncClient

    transport = HttpA2ATransport()
    transport._httpx = FakeHttpx()  # noqa: SLF001

    normalized = await transport.send(signal, endpoint="https://example.com/a2a")
    assert normalized.signal_id == "sig-remote"
    assert normalized.payload["query"] == "map patents"
