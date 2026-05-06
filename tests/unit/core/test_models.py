from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from bca2p.core import (
    CORE_SCHEMA_VERSION,
    AgentProfile,
    ArtifactRef,
    CausalFeedback,
    ComplexSpec,
    ContributionFactor,
    FeedbackType,
    HomeostasisPolicy,
    PriorityLevel,
    QuorumRule,
    ReceptorSpec,
    RoutingError,
    SCHEMA_METADATA_KEY,
    SchemaVersionError,
    SignalEnvelope,
    SignalMode,
    SignalValidationError,
    TopologyPolicy,
    TopologyStrategy,
    TrustLevel,
    TrustPolicyError,
)


class DemoPayload(BaseModel):
    query: str
    retries: int


def make_signal_payload() -> dict[str, Any]:
    return {
        "signal_id": "sig-1",
        "mode": SignalMode.PARACRINE,
        "sender": "planner",
        "recipient_scope": "research.team",
        "receptor": "research.query",
        "payload": {"query": "map patents", "retries": 1},
        "priority": PriorityLevel.HIGH,
        "ttl": 30.0,
        "decay": 0.25,
        "amplification": 2.0,
        "confidence": 0.9,
        "trace_path": ["planner"],
        "trust_level": TrustLevel.TRUSTED,
        "policy_tags": ["benchmark", "phase2"],
        "artifact_refs": [
            ArtifactRef(
                artifact_id="artifact-1",
                uri="memory://artifact-1",
                media_type="application/json",
            )
        ],
    }


def test_signal_mode_contains_stable_and_helper_values() -> None:
    assert SignalMode.AUTOCRINE == "autocrine"
    assert SignalMode.SYNAPTIC == "synaptic"
    assert SignalMode.VESICLE == "vesicle"
    assert SignalMode.QUORUM == "quorum"


def test_signal_envelope_round_trip_with_schema_stamp() -> None:
    envelope = SignalEnvelope(**make_signal_payload())
    data = envelope.to_dict()

    assert data[SCHEMA_METADATA_KEY] == {
        "name": "signal_envelope",
        "version": CORE_SCHEMA_VERSION,
    }

    round_tripped = SignalEnvelope.from_dict(data)
    assert round_tripped == envelope


def test_signal_envelope_to_dict_can_skip_schema_stamp() -> None:
    envelope = SignalEnvelope(**make_signal_payload())
    data = envelope.to_dict(stamp_version=False)
    assert SCHEMA_METADATA_KEY not in data


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("ttl", -1.0),
        ("decay", 1.5),
        ("amplification", -0.1),
        ("confidence", 2.0),
    ],
)
def test_signal_envelope_rejects_invalid_numeric_bounds(field_name: str, value: float) -> None:
    payload = make_signal_payload()
    payload[field_name] = value
    with pytest.raises(ValidationError):
        SignalEnvelope(**payload)


def test_signal_envelope_requires_non_empty_identity_fields() -> None:
    payload = make_signal_payload()
    payload["signal_id"] = "   "
    with pytest.raises(ValidationError):
        SignalEnvelope(**payload)


def test_schema_version_mismatch_raises() -> None:
    envelope = SignalEnvelope(**make_signal_payload())
    data = envelope.to_dict()
    data[SCHEMA_METADATA_KEY]["version"] = "999.0"
    with pytest.raises(SchemaVersionError):
        SignalEnvelope.from_dict(data)


def test_schema_name_mismatch_raises() -> None:
    envelope = SignalEnvelope(**make_signal_payload())
    data = envelope.to_dict()
    data[SCHEMA_METADATA_KEY]["name"] = "wrong_name"
    with pytest.raises(SchemaVersionError):
        SignalEnvelope.from_dict(data)


def test_artifact_ref_requires_non_empty_fields() -> None:
    with pytest.raises(ValidationError):
        ArtifactRef(artifact_id="", uri="memory://artifact")


def test_receptor_spec_can_bind_and_validate_payload_model() -> None:
    receptor = ReceptorSpec.from_payload_model(
        receptor_id="research.query",
        payload_model=DemoPayload,
        accepted_modes=[SignalMode.PARACRINE, SignalMode.SYNAPTIC],
        trust_requirement=TrustLevel.TRUSTED,
        cooldown_seconds=5.0,
        desensitization_factor=0.3,
    )

    assert receptor.payload_schema == f"{DemoPayload.__module__}.{DemoPayload.__qualname__}"
    validated = receptor.validate_payload({"query": "map patents", "retries": 2})
    assert validated == {"query": "map patents", "retries": 2}


def test_receptor_spec_rejects_invalid_payload() -> None:
    receptor = ReceptorSpec.from_payload_model(
        receptor_id="research.query",
        payload_model=DemoPayload,
        accepted_modes=[SignalMode.PARACRINE],
    )
    with pytest.raises(ValidationError):
        receptor.validate_payload({"query": "missing retries"})


def test_receptor_spec_rejects_invalid_config() -> None:
    with pytest.raises(ValidationError):
        ReceptorSpec(
            receptor_id="research.query",
            accepted_modes=[],
        )


def test_complex_spec_validates_member_bounds_and_uniqueness() -> None:
    with pytest.raises(ValidationError):
        ComplexSpec(
            scaffold_id="research_complex",
            members=["a"],
            min_members=2,
        )

    with pytest.raises(ValidationError):
        ComplexSpec(
            scaffold_id="research_complex",
            members=["a", "a"],
        )

    spec = ComplexSpec(
        scaffold_id="research_complex",
        members=["a", "b"],
        min_members=2,
        max_members=3,
    )
    assert spec.members == ["a", "b"]


def test_quorum_rule_validates_thresholds_and_participant_count() -> None:
    with pytest.raises(ValidationError):
        QuorumRule(rule_id="escalate", target_scope="support", threshold=1.1)
    with pytest.raises(ValidationError):
        QuorumRule(rule_id="escalate", target_scope="support", threshold=0.7, min_participants=0)

    rule = QuorumRule(rule_id="escalate", target_scope="support", threshold=0.75)
    assert rule.metric == "count"


def test_homeostasis_policy_default_and_bounds() -> None:
    policy = HomeostasisPolicy.default()
    assert policy.policy_id == "default"
    assert policy.max_amplification == 80.0

    with pytest.raises(ValidationError):
        HomeostasisPolicy(max_inflight_signals=0)


def test_topology_policy_validates_weights_and_neighbors() -> None:
    policy = TopologyPolicy(
        policy_id="balanced",
        strategy=TopologyStrategy.BALANCED,
        max_neighbors=4,
        affinity_weight=1.5,
        urgency_weight=0.5,
        history_weight=0.25,
        trust_weight=2.0,
    )
    assert policy.strategy == TopologyStrategy.BALANCED

    with pytest.raises(ValidationError):
        TopologyPolicy(policy_id="bad", max_neighbors=0)


def test_causal_feedback_and_contribution_factor_validate_bounds() -> None:
    feedback = CausalFeedback(
        target_signal_id="sig-1",
        feedback_type=FeedbackType.OUTCOME,
        outcome="success",
        confidence=0.88,
        contributors=[
            ContributionFactor(source_id="planner", contribution=0.7, reason="strong routing"),
            ContributionFactor(source_id="critic", contribution=0.2),
        ],
    )
    assert feedback.feedback_type == FeedbackType.OUTCOME

    with pytest.raises(ValidationError):
        ContributionFactor(source_id="planner", contribution=2.0)


def test_agent_profile_requires_unique_receptor_ids() -> None:
    receptor_a = ReceptorSpec(
        receptor_id="research.query",
        accepted_modes=[SignalMode.PARACRINE],
    )
    receptor_b = ReceptorSpec(
        receptor_id="research.query",
        accepted_modes=[SignalMode.SYNAPTIC],
    )

    with pytest.raises(ValidationError):
        AgentProfile(
            agent_id="researcher",
            receptors=[receptor_a, receptor_b],
        )


def test_agent_profile_round_trip_serialization() -> None:
    receptor = ReceptorSpec(
        receptor_id="research.query",
        accepted_modes=[SignalMode.PARACRINE],
        trust_requirement=TrustLevel.INTERNAL,
    )
    profile = AgentProfile(
        agent_id="researcher",
        display_name="Research Agent",
        receptors=[receptor],
        scopes=["research.team"],
    )
    restored = AgentProfile.from_dict(profile.to_dict())
    assert restored == profile


def test_core_exceptions_have_expected_inheritance() -> None:
    assert issubclass(SchemaVersionError, Exception)
    assert issubclass(RoutingError, Exception)
    assert issubclass(SignalValidationError, Exception)
    assert issubclass(TrustPolicyError, Exception)
