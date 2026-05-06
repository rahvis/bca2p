"""Typed protocol models for the bca2p core layer."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from .base import ProtocolModel
from .enums import FeedbackType, PriorityLevel, SignalMode, TopologyStrategy, TrustLevel


def _qualname_for_model(model_cls: type[BaseModel]) -> str:
    return f"{model_cls.__module__}.{model_cls.__qualname__}"


class ArtifactRef(ProtocolModel):
    """Reference to an external or attached artifact carried with a signal."""

    schema_name = "artifact_ref"

    artifact_id: str
    uri: str
    media_type: str | None = None
    checksum: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("artifact_id", "uri")
    @classmethod
    def _require_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value


class ReceptorSpec(ProtocolModel):
    """Typed receptor contract used for signal delivery and payload validation."""

    schema_name = "receptor_spec"

    receptor_id: str
    payload_schema: str | None = None
    accepted_modes: list[SignalMode]
    trust_requirement: TrustLevel = TrustLevel.INTERNAL
    cooldown_seconds: float = 0.0
    desensitization_factor: float = 0.0
    affinity_score: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    payload_model: type[BaseModel] | None = Field(default=None, exclude=True, repr=False)

    @field_validator("receptor_id")
    @classmethod
    def _validate_receptor_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("receptor_id must not be empty")
        return value

    @field_validator("accepted_modes")
    @classmethod
    def _require_modes(cls, value: list[SignalMode]) -> list[SignalMode]:
        if not value:
            raise ValueError("accepted_modes must contain at least one signal mode")
        return value

    @field_validator("cooldown_seconds")
    @classmethod
    def _cooldown_non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("cooldown_seconds must be non-negative")
        return value

    @field_validator("desensitization_factor")
    @classmethod
    def _desensitization_bounds(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("desensitization_factor must be between 0.0 and 1.0")
        return value

    @field_validator("affinity_score")
    @classmethod
    def _affinity_non_negative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("affinity_score must be non-negative")
        return value

    @model_validator(mode="after")
    def _derive_payload_schema(self) -> "ReceptorSpec":
        if self.payload_model is not None and self.payload_schema is None:
            self.payload_schema = _qualname_for_model(self.payload_model)
        return self

    @classmethod
    def from_payload_model(
        cls,
        *,
        receptor_id: str,
        payload_model: type[BaseModel],
        accepted_modes: list[SignalMode],
        trust_requirement: TrustLevel = TrustLevel.INTERNAL,
        cooldown_seconds: float = 0.0,
        desensitization_factor: float = 0.0,
        affinity_score: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ReceptorSpec":
        return cls(
            receptor_id=receptor_id,
            payload_model=payload_model,
            payload_schema=_qualname_for_model(payload_model),
            accepted_modes=accepted_modes,
            trust_requirement=trust_requirement,
            cooldown_seconds=cooldown_seconds,
            desensitization_factor=desensitization_factor,
            affinity_score=affinity_score,
            metadata=metadata or {},
        )

    def validate_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        if self.payload_model is None:
            return payload
        validated = self.payload_model.model_validate(payload)
        return validated.model_dump(mode="python")


class ComplexSpec(ProtocolModel):
    """Definition for a temporary signaling complex or coalition."""

    schema_name = "complex_spec"

    scaffold_id: str
    members: list[str] = Field(default_factory=list)
    min_members: int = 2
    max_members: int | None = None
    shared_state_channel: str | None = None
    ttl_seconds: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("scaffold_id")
    @classmethod
    def _scaffold_id_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("scaffold_id must not be empty")
        return value

    @field_validator("ttl_seconds")
    @classmethod
    def _ttl_non_negative(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("ttl_seconds must be non-negative")
        return value

    @model_validator(mode="after")
    def _validate_member_bounds(self) -> "ComplexSpec":
        if self.min_members < 1:
            raise ValueError("min_members must be at least 1")
        if self.max_members is not None and self.max_members < self.min_members:
            raise ValueError("max_members must be greater than or equal to min_members")
        if self.members and len(set(self.members)) != len(self.members):
            raise ValueError("members must be unique")
        if self.members and len(self.members) < self.min_members:
            raise ValueError("members must satisfy min_members")
        if self.max_members is not None and len(self.members) > self.max_members:
            raise ValueError("members exceeds max_members")
        return self


class QuorumRule(ProtocolModel):
    """Threshold rule for triggering group-level actions."""

    schema_name = "quorum_rule"

    rule_id: str
    target_scope: str
    threshold: float
    metric: str = "count"
    min_participants: int = 1
    action: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("rule_id", "target_scope", "metric")
    @classmethod
    def _non_empty_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value

    @field_validator("threshold")
    @classmethod
    def _threshold_bounds(cls, value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("threshold must be between 0.0 and 1.0")
        return value

    @field_validator("min_participants")
    @classmethod
    def _participants_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("min_participants must be at least 1")
        return value


class HomeostasisPolicy(ProtocolModel):
    """Policy used to stabilize runtime communication behavior."""

    schema_name = "homeostasis_policy"

    policy_id: str = "default"
    max_inflight_signals: int = 1024
    max_amplification: float = 80.0
    cooldown_seconds: float = 1.0
    noisy_sender_threshold: int = 100
    topology_update_rate_limit: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def default(cls) -> "HomeostasisPolicy":
        return cls()

    @field_validator("policy_id")
    @classmethod
    def _policy_id_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("policy_id must not be empty")
        return value

    @field_validator(
        "max_inflight_signals",
        "noisy_sender_threshold",
    )
    @classmethod
    def _positive_ints(cls, value: int) -> int:
        if value < 1:
            raise ValueError("value must be at least 1")
        return value

    @field_validator(
        "max_amplification",
        "cooldown_seconds",
        "topology_update_rate_limit",
    )
    @classmethod
    def _non_negative_floats(cls, value: float) -> float:
        if value < 0:
            raise ValueError("value must be non-negative")
        return value


class TopologyPolicy(ProtocolModel):
    """Policy controlling adaptive communication topology behavior."""

    schema_name = "topology_policy"

    policy_id: str
    strategy: TopologyStrategy = TopologyStrategy.BALANCED
    max_neighbors: int = 8
    affinity_weight: float = 1.0
    urgency_weight: float = 1.0
    history_weight: float = 1.0
    trust_weight: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("policy_id")
    @classmethod
    def _policy_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("policy_id must not be empty")
        return value

    @field_validator("max_neighbors")
    @classmethod
    def _neighbors_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("max_neighbors must be at least 1")
        return value

    @field_validator(
        "affinity_weight",
        "urgency_weight",
        "history_weight",
        "trust_weight",
    )
    @classmethod
    def _weights_non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("weights must be non-negative")
        return value


class ContributionFactor(ProtocolModel):
    """Structured contribution estimate for causal feedback attribution."""

    schema_name = "contribution_factor"

    source_id: str
    contribution: float
    reason: str | None = None

    @field_validator("source_id")
    @classmethod
    def _source_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("source_id must not be empty")
        return value

    @field_validator("contribution")
    @classmethod
    def _contribution_bounds(cls, value: float) -> float:
        if not -1.0 <= value <= 1.0:
            raise ValueError("contribution must be between -1.0 and 1.0")
        return value


class CausalFeedback(ProtocolModel):
    """Structured downstream feedback used for causal learning and adaptation."""

    schema_name = "causal_feedback"

    target_signal_id: str
    feedback_type: FeedbackType
    outcome: str
    confidence: float | None = None
    contributors: list[ContributionFactor] = Field(default_factory=list)
    counterfactuals: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("target_signal_id", "outcome")
    @classmethod
    def _required_strings(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value

    @field_validator("confidence")
    @classmethod
    def _confidence_bounds(cls, value: float | None) -> float | None:
        if value is not None and not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value


class AgentProfile(ProtocolModel):
    """Describes an agent and its publicly routable receptor capabilities."""

    schema_name = "agent_profile"

    agent_id: str
    display_name: str | None = None
    description: str | None = None
    version: str = "1.0"
    trust_level: TrustLevel = TrustLevel.INTERNAL
    scopes: list[str] = Field(default_factory=list)
    receptors: list[ReceptorSpec] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("agent_id", "version")
    @classmethod
    def _agent_fields_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value

    @model_validator(mode="after")
    def _unique_receptors(self) -> "AgentProfile":
        receptor_ids = [receptor.receptor_id for receptor in self.receptors]
        if len(set(receptor_ids)) != len(receptor_ids):
            raise ValueError("receptor_ids in an AgentProfile must be unique")
        return self


class SignalEnvelope(ProtocolModel):
    """Canonical signal envelope used for inter-agent communication."""

    schema_name = "signal_envelope"

    signal_id: str
    mode: SignalMode
    sender: str
    recipient_scope: str
    receptor: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: PriorityLevel = PriorityLevel.MEDIUM
    ttl: float | None = None
    decay: float | None = None
    amplification: float = 1.0
    confidence: float | None = None
    causal_parent_id: str | None = None
    correlation_id: str | None = None
    trace_path: list[str] = Field(default_factory=list)
    trust_level: TrustLevel | None = None
    policy_tags: list[str] = Field(default_factory=list)
    artifact_refs: list[ArtifactRef] = Field(default_factory=list)

    @field_validator("signal_id", "sender", "recipient_scope")
    @classmethod
    def _required_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be empty")
        return value

    @field_validator("receptor")
    @classmethod
    def _receptor_if_present_non_empty(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("receptor must not be empty when provided")
        return value

    @field_validator("ttl")
    @classmethod
    def _ttl_positive(cls, value: float | None) -> float | None:
        if value is not None and value < 0:
            raise ValueError("ttl must be non-negative")
        return value

    @field_validator("decay")
    @classmethod
    def _decay_bounds(cls, value: float | None) -> float | None:
        if value is not None and not 0.0 <= value <= 1.0:
            raise ValueError("decay must be between 0.0 and 1.0")
        return value

    @field_validator("amplification")
    @classmethod
    def _amplification_non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("amplification must be non-negative")
        return value

    @field_validator("confidence")
    @classmethod
    def _signal_confidence_bounds(cls, value: float | None) -> float | None:
        if value is not None and not 0.0 <= value <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return value
