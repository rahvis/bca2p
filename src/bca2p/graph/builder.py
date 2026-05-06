"""Graph builder implementation for bca2p."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from bca2p.core import ComplexSpec, HomeostasisPolicy, QuorumRule, ReceptorSpec

from .channels import AggregateChannel, BaseChannel, EphemeralChannel, LastValueChannel, TopicChannel
from .exceptions import GraphValidationError
from .models import CompiledBioGraph, CompiledComplex
from .nodes import BioNode, BioNodeHandler


ChannelFactory = Callable[..., BaseChannel]


class BioGraph:
    """Authoring surface for bio-inspired agent workflows."""

    def __init__(
        self,
        *,
        state_schema: type[Any] | None = None,
        context_schema: type[Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.state_schema = state_schema
        self.context_schema = context_schema
        self.metadata = metadata or {}
        self._nodes: dict[str, BioNode] = {}
        self._channels: dict[str, BaseChannel] = {}
        self._complexes: dict[str, ComplexSpec] = {}
        self._quorum_rules: dict[str, QuorumRule] = {}
        self._homeostasis_policy: HomeostasisPolicy | None = None

    def add_agent(
        self,
        name: str,
        handler: BioNodeHandler,
        *,
        receptors: list[ReceptorSpec] | None = None,
        scope_subscriptions: list[str] | None = None,
        topology_subscriptions: list[str] | None = None,
        input_channels: list[str] | None = None,
        output_channel: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> BioNode:
        if name in self._nodes:
            raise GraphValidationError(f"Agent {name!r} is already registered")

        node = BioNode(
            node_id=name,
            handler=handler,
            receptors=receptors or [],
            scope_subscriptions=scope_subscriptions or [],
            topology_subscriptions=topology_subscriptions or [],
            input_channels=input_channels or [],
            output_channel=output_channel,
            metadata=metadata or {},
        )
        self._nodes[name] = node
        return node

    def add_channel(
        self,
        name: str,
        *,
        mode: str = "topic",
        default: Any = None,
        reducer: Callable[[Any, Any], Any] | None = None,
        accumulate: bool = True,
        deduplicate: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> BaseChannel:
        if name in self._channels:
            raise GraphValidationError(f"Channel {name!r} is already registered")
        if not name.strip():
            raise GraphValidationError("Channel name must not be empty")

        channel: BaseChannel
        channel_metadata = metadata or {}
        if mode == "last_value":
            channel = LastValueChannel(name=name, value=default, metadata=channel_metadata)
        elif mode == "topic":
            seed = list(default) if default is not None else []
            channel = TopicChannel(
                name=name,
                value=seed,
                accumulate=accumulate,
                deduplicate=deduplicate,
                metadata=channel_metadata,
            )
        elif mode == "aggregate":
            if reducer is None:
                raise GraphValidationError("Aggregate channels require a reducer")
            channel = AggregateChannel(
                name=name,
                reducer=reducer,
                initial_value=default,
                metadata=channel_metadata,
            )
        elif mode == "ephemeral":
            channel = EphemeralChannel(name=name, value=default, metadata=channel_metadata)
        else:
            raise GraphValidationError(f"Unsupported channel mode: {mode!r}")

        self._channels[name] = channel
        return channel

    def add_complex_policy(self, complex_spec: ComplexSpec) -> ComplexSpec:
        if complex_spec.scaffold_id in self._complexes:
            raise GraphValidationError(
                f"Complex {complex_spec.scaffold_id!r} is already registered",
            )
        self._complexes[complex_spec.scaffold_id] = complex_spec
        return complex_spec

    def add_quorum_rule(self, rule: QuorumRule) -> QuorumRule:
        if rule.rule_id in self._quorum_rules:
            raise GraphValidationError(f"Quorum rule {rule.rule_id!r} is already registered")
        self._quorum_rules[rule.rule_id] = rule
        return rule

    def add_homeostasis(self, policy: HomeostasisPolicy) -> HomeostasisPolicy:
        self._homeostasis_policy = policy
        return policy

    @property
    def nodes(self) -> dict[str, BioNode]:
        return dict(self._nodes)

    @property
    def channels(self) -> dict[str, BaseChannel]:
        return dict(self._channels)

    def compile(self, **runtime_kwargs: Any) -> CompiledBioGraph:
        self._validate()
        return CompiledBioGraph(
            nodes={name: deepcopy(node) for name, node in self._nodes.items()},
            channels={name: channel.clone() for name, channel in self._channels.items()},
            complexes={
                scaffold_id: CompiledComplex(spec=deepcopy(spec))
                for scaffold_id, spec in self._complexes.items()
            },
            quorum_rules={rule_id: deepcopy(rule) for rule_id, rule in self._quorum_rules.items()},
            homeostasis_policy=deepcopy(self._homeostasis_policy),
            metadata={
                "state_schema": getattr(self.state_schema, "__name__", None),
                "context_schema": getattr(self.context_schema, "__name__", None),
                "runtime_kwargs": runtime_kwargs,
            },
        )

    def _validate(self) -> None:
        self._validate_channel_references()
        self._validate_receptor_ids()
        self._validate_quorum_rules()
        self._validate_orphan_agents()

    def _validate_channel_references(self) -> None:
        channel_names = set(self._channels)

        for node in self._nodes.values():
            missing_inputs = [name for name in node.input_channels if name not in channel_names]
            if missing_inputs:
                raise GraphValidationError(
                    f"Agent {node.node_id!r} references missing input channels: {missing_inputs}",
                )
            if node.output_channel is not None and node.output_channel not in channel_names:
                raise GraphValidationError(
                    f"Agent {node.node_id!r} references missing output channel "
                    f"{node.output_channel!r}",
                )

        for complex_spec in self._complexes.values():
            if (
                complex_spec.shared_state_channel is not None
                and complex_spec.shared_state_channel not in channel_names
            ):
                raise GraphValidationError(
                    f"Complex {complex_spec.scaffold_id!r} references missing shared_state_channel "
                    f"{complex_spec.shared_state_channel!r}",
                )

    def _validate_receptor_ids(self) -> None:
        seen: dict[str, str] = {}
        for node in self._nodes.values():
            for receptor in node.receptors:
                owner = seen.get(receptor.receptor_id)
                if owner is not None:
                    raise GraphValidationError(
                        f"Duplicate receptor_id {receptor.receptor_id!r} found on agents "
                        f"{owner!r} and {node.node_id!r}",
                    )
                seen[receptor.receptor_id] = node.node_id

    def _validate_quorum_rules(self) -> None:
        known_scopes = set()
        for node in self._nodes.values():
            known_scopes.update(node.scope_subscriptions)
            for receptor in node.receptors:
                known_scopes.update(receptor.metadata.get("scopes", []))

        known_scopes.update(self.metadata.get("scopes", []))

        for rule in self._quorum_rules.values():
            if rule.target_scope == "*":
                continue
            if rule.target_scope not in known_scopes:
                raise GraphValidationError(
                    f"Quorum rule {rule.rule_id!r} targets unknown scope "
                    f"{rule.target_scope!r}",
                )

    def _validate_orphan_agents(self) -> None:
        complex_members = {
            member
            for complex_spec in self._complexes.values()
            for member in complex_spec.members
        }

        for node in self._nodes.values():
            connected = any(
                [
                    bool(node.receptors),
                    bool(node.scope_subscriptions),
                    bool(node.topology_subscriptions),
                    bool(node.input_channels),
                    node.output_channel is not None,
                    node.node_id in complex_members,
                ],
            )
            if not connected:
                raise GraphValidationError(
                    f"Agent {node.node_id!r} is orphaned: it has no receptors, subscriptions, "
                    "channel bindings, or complex membership",
                )
