"""Stable checkpointed runtime for executing compiled bio-graphs."""

from __future__ import annotations

import asyncio
import math
from copy import deepcopy
from dataclasses import replace
from typing import TYPE_CHECKING, Any

from bca2p.core import PriorityLevel, SignalEnvelope, SignalMode
from bca2p.graph import BioNode, CompiledBioGraph, ComplexLifecycleState, EphemeralChannel

from .checkpoint import Checkpointer, InMemoryCheckpointer
from .exceptions import ReplayError, RuntimeExecutionError
from .models import RuntimeConfig, RuntimeResult, StateSnapshot

if TYPE_CHECKING:
    from bca2p.observability import TraceRecorder
    from bca2p.observability.models import RuntimeEventType


class BioRuntime:
    """Stable local runtime with super-step execution and checkpointing."""

    def __init__(
        self,
        graph: CompiledBioGraph,
        *,
        checkpointer: Checkpointer | None = None,
        config: RuntimeConfig | None = None,
        trace_recorder: "TraceRecorder | None" = None,
    ) -> None:
        self.graph = graph
        self.checkpointer = checkpointer or InMemoryCheckpointer()
        runtime_kwargs = graph.metadata.get("runtime_kwargs", {})
        derived_config = RuntimeConfig(**runtime_kwargs) if runtime_kwargs else RuntimeConfig()
        self.config = config or derived_config
        self.trace_recorder = trace_recorder
        self._last_snapshot_id: str | None = None
        self._snapshot_counter = 0

    def invoke(
        self,
        input_state: Any | None = None,
        *,
        context: dict[str, Any] | None = None,
        checkpoint_id: str | None = None,
    ) -> RuntimeResult:
        return asyncio.run(self.ainvoke(input_state, context=context, checkpoint_id=checkpoint_id))

    async def ainvoke(
        self,
        input_state: Any | None = None,
        *,
        context: dict[str, Any] | None = None,
        checkpoint_id: str | None = None,
    ) -> RuntimeResult:
        state, pending_signals, start_step = self._restore_or_initialize(
            input_state=input_state,
            context=context,
            checkpoint_id=checkpoint_id,
        )

        completed = True
        final_snapshot: StateSnapshot | None = None
        active_node_ids = self._initial_active_nodes() if start_step == 0 else []

        for step in range(start_step, self.config.max_steps):
            if step > start_step or start_step > 0:
                active_node_ids = self._plan_active_nodes(
                    pending_signals=pending_signals,
                    updated_channels=final_snapshot.updated_channels if final_snapshot else [],
                    step=step,
                )

            if not active_node_ids:
                break

            execution = await self._execute_step(
                state=state,
                active_node_ids=active_node_ids,
                pending_signals=pending_signals,
                step=step,
            )

            state = execution["state"]
            pending_signals = execution["pending_signals"]
            final_snapshot = self._create_snapshot(
                step=step,
                state=state,
                pending_signals=pending_signals,
                active_nodes=active_node_ids,
                updated_channels=execution["updated_channels"],
                context=context or {},
            )
            self.checkpointer.save(final_snapshot)
            self._last_snapshot_id = final_snapshot.snapshot_id
            if self.trace_recorder is not None:
                self.trace_recorder.record_topology_snapshot(self.graph, step=step)

            if not pending_signals and not execution["updated_channels"]:
                break
        else:
            completed = False

        steps_executed = 0 if final_snapshot is None else final_snapshot.step + 1
        return RuntimeResult(
            final_state=state,
            final_snapshot=final_snapshot,
            steps_executed=steps_executed,
            completed=completed,
        )

    def get_state(self, checkpoint_id: str | None = None) -> StateSnapshot | None:
        if checkpoint_id is not None:
            return self.checkpointer.get(checkpoint_id)
        if self._last_snapshot_id is None:
            return None
        return self.checkpointer.get(self._last_snapshot_id)

    def get_state_history(self) -> list[StateSnapshot]:
        return self.checkpointer.history()

    def replay(self, checkpoint_id: str | None = None) -> RuntimeResult:
        if checkpoint_id is None:
            history = self.get_state_history()
            if not history:
                raise ReplayError("No checkpoints available for replay")
            checkpoint_id = history[0].snapshot_id
        snapshot = self.checkpointer.get(checkpoint_id)
        if snapshot is None:
            raise ReplayError(f"Checkpoint {checkpoint_id!r} not found")
        return self.invoke(
            deepcopy(snapshot.state),
            context=dict(snapshot.metadata.get("context", {})),
            checkpoint_id=checkpoint_id,
        )

    def fork_replay(
        self,
        checkpoint_id: str,
        *,
        state_update: Any | None = None,
        as_node: str | None = None,
    ) -> RuntimeResult:
        snapshot = self.checkpointer.get(checkpoint_id)
        if snapshot is None:
            raise ReplayError(f"Checkpoint {checkpoint_id!r} not found")

        state = deepcopy(snapshot.state)
        if state_update is not None:
            if isinstance(state, dict) and isinstance(state_update, dict):
                state = {**state, **state_update}
            else:
                state = state_update

        context = dict(snapshot.metadata.get("context", {}))
        if as_node is not None:
            context["fork_as_node"] = as_node
        return self.invoke(state, context=context, checkpoint_id=checkpoint_id)

    def _restore_or_initialize(
        self,
        *,
        input_state: Any | None,
        context: dict[str, Any] | None,
        checkpoint_id: str | None,
    ) -> tuple[Any, list[SignalEnvelope], int]:
        if checkpoint_id is None:
            state = deepcopy(input_state) if input_state is not None else {}
            return state, [], 0

        snapshot = self.checkpointer.get(checkpoint_id)
        if snapshot is None:
            raise ReplayError(f"Checkpoint {checkpoint_id!r} not found")

        restored_state = deepcopy(snapshot.state)
        if input_state is not None:
            if isinstance(restored_state, dict) and isinstance(input_state, dict):
                restored_state.update(deepcopy(input_state))
            else:
                restored_state = deepcopy(input_state)

        self._restore_channels(snapshot.channel_values)
        self._restore_complexes(snapshot.complex_states)
        pending_signals = [deepcopy(signal) for signal in snapshot.pending_signals]
        return restored_state, pending_signals, snapshot.step + 1

    def _restore_channels(self, channel_values: dict[str, Any]) -> None:
        for name, value in channel_values.items():
            if name in self.graph.channels:
                self.graph.channels[name].value = deepcopy(value)  # type: ignore[attr-defined]

    def _restore_complexes(self, complex_states: dict[str, ComplexLifecycleState]) -> None:
        for scaffold_id, state in complex_states.items():
            if scaffold_id in self.graph.complexes:
                self.graph.set_complex_state(scaffold_id, state)

    def _initial_active_nodes(self) -> list[str]:
        entrypoints = [
            node.node_id
            for node in self.graph.nodes.values()
            if not node.input_channels or node.metadata.get("entrypoint") is True
        ]
        return entrypoints or list(self.graph.nodes.keys())

    def _plan_active_nodes(
        self,
        *,
        pending_signals: list[SignalEnvelope],
        updated_channels: list[str],
        step: int,
    ) -> list[str]:
        active: list[str] = []
        updated_set = set(updated_channels)

        for node in self.graph.nodes.values():
            channel_trigger = bool(updated_set.intersection(node.input_channels))
            signal_trigger = any(node.matches_signal(signal) for signal in pending_signals)
            if channel_trigger or signal_trigger:
                active.append(node.node_id)

        if not active and step == 0:
            return self._initial_active_nodes()
        return active

    async def _execute_step(
        self,
        *,
        state: Any,
        active_node_ids: list[str],
        pending_signals: list[SignalEnvelope],
        step: int,
    ) -> dict[str, Any]:
        output_updates: dict[str, list[Any]] = {}
        emitted_signals: list[SignalEnvelope] = []

        for node_id in active_node_ids:
            node = self.graph.get_node(node_id)
            node_input = self._build_node_input(
                state=state,
                node=node,
                pending_signals=pending_signals,
                step=step,
            )
            context = node.create_context()
            context.metadata.update(
                {
                    "step": step,
                    "input_channels": list(node.input_channels),
                    "matched_signal_ids": [
                        signal.signal_id for signal in pending_signals if node.matches_signal(signal)
                    ],
                }
            )
            matched_signals = [signal for signal in pending_signals if node.matches_signal(signal)]
            for signal in matched_signals:
                self._record_event(
                    "SIGNAL_DELIVERED",
                    step=step,
                    node_id=node.node_id,
                    signal_id=signal.signal_id,
                    details={
                        "sender": signal.sender,
                        "recipient_scope": signal.recipient_scope,
                        "receptor": signal.receptor,
                    },
                )
            result = await self._invoke_node(node, node_input, context)
            if node.output_channel is not None and result is not None:
                output_updates.setdefault(node.output_channel, []).append(result)
            for signal in context.emitter.emitted_signals:
                self._record_event(
                    "SIGNAL_EMITTED",
                    step=step,
                    node_id=node.node_id,
                    signal_id=signal.signal_id,
                    details={
                        "sender": signal.sender,
                        "recipient_scope": signal.recipient_scope,
                        "receptor": signal.receptor,
                        "amplification": signal.amplification,
                        "mode": signal.mode.value,
                    },
                )
            emitted_signals.extend(context.emitter.emitted_signals)

        updated_channels = self._apply_channel_updates(output_updates)
        normalized_signals = self._normalize_signals(emitted_signals)
        quorum_signals = self._evaluate_quorum_signals(normalized_signals)
        next_pending_signals = normalized_signals + quorum_signals
        self._advance_complex_lifecycle(active_node_ids=active_node_ids, updated_channels=updated_channels)

        return {
            "state": self._update_graph_state(state, output_updates),
            "pending_signals": next_pending_signals,
            "updated_channels": updated_channels,
        }

    def _build_node_input(
        self,
        *,
        state: Any,
        node: BioNode,
        pending_signals: list[SignalEnvelope],
        step: int,
    ) -> Any:
        matched_signals = [
            deepcopy(signal) for signal in pending_signals if node.matches_signal(signal)
        ]
        channel_values = {
            channel_name: deepcopy(self.graph.get_channel(channel_name).read())
            for channel_name in node.input_channels
        }

        if isinstance(state, dict):
            merged_state = deepcopy(state)
            merged_state.update(
                {
                    "__channels__": channel_values,
                    "__signals__": [signal.to_dict() for signal in matched_signals],
                    "__step__": step,
                    "__node_id__": node.node_id,
                }
            )
            return merged_state

        return {
            "graph_state": deepcopy(state),
            "channels": channel_values,
            "signals": [signal.to_dict() for signal in matched_signals],
            "step": step,
            "node_id": node.node_id,
        }

    async def _invoke_node(
        self,
        node: BioNode,
        node_input: Any,
        context: Any,
    ) -> Any:
        for attempt in range(self.config.max_retries + 1):
            try:
                invocation = node.invoke(node_input, context=context)
                if node.is_async:
                    if self.config.step_timeout_seconds is not None:
                        return await asyncio.wait_for(
                            invocation,
                            timeout=self.config.step_timeout_seconds,
                        )
                    return await invocation

                if self.config.step_timeout_seconds is not None:
                    return await asyncio.wait_for(
                        asyncio.to_thread(lambda: invocation),
                        timeout=self.config.step_timeout_seconds,
                    )
                return invocation
            except Exception as exc:  # noqa: BLE001
                if attempt >= self.config.max_retries:
                    raise RuntimeExecutionError(
                        f"Node {node.node_id!r} failed after {attempt + 1} attempts",
                    ) from exc
                if self.config.retry_backoff_seconds > 0:
                    await asyncio.sleep(self.config.retry_backoff_seconds)
        raise RuntimeExecutionError(f"Node {node.node_id!r} failed unexpectedly")

    def _apply_channel_updates(self, updates: dict[str, list[Any]]) -> list[str]:
        updated_channels: list[str] = []
        for channel_name, values in updates.items():
            self.graph.get_channel(channel_name).apply_updates(values)
            updated_channels.append(channel_name)
        return updated_channels

    def _normalize_signals(self, signals: list[SignalEnvelope]) -> list[SignalEnvelope]:
        max_amplification = (
            self.graph.homeostasis_policy.max_amplification
            if self.graph.homeostasis_policy is not None
            else math.inf
        )
        normalized: list[SignalEnvelope] = []
        for signal in signals:
            ttl = signal.ttl
            if ttl is not None:
                ttl = max(0.0, ttl - 1.0)
                if signal.decay is not None:
                    ttl = ttl * max(0.0, 1.0 - signal.decay)
                if ttl <= 0:
                    self._record_event(
                        "SIGNAL_DROPPED",
                        step=self._current_step_from_signal(signal),
                        signal_id=signal.signal_id,
                        details={
                            "sender": signal.sender,
                            "reason": "ttl_expired",
                        },
                    )
                    continue
            if signal.amplification > max_amplification:
                self._record_event(
                    "HOMEOSTASIS_INTERVENTION",
                    step=self._current_step_from_signal(signal),
                    signal_id=signal.signal_id,
                    details={
                        "sender": signal.sender,
                        "action": "cap_amplification",
                        "requested": signal.amplification,
                        "capped_to": max_amplification,
                    },
                )

            normalized.append(
                replace(
                    signal,
                    amplification=min(signal.amplification, max_amplification),
                    ttl=ttl,
                )
            )
        return normalized

    def _evaluate_quorum_signals(self, pending_signals: list[SignalEnvelope]) -> list[SignalEnvelope]:
        quorum_signals: list[SignalEnvelope] = []
        counts_by_scope: dict[str, int] = {}
        unique_senders_by_scope: dict[str, set[str]] = {}
        for signal in pending_signals:
            counts_by_scope[signal.recipient_scope] = counts_by_scope.get(signal.recipient_scope, 0) + 1
            unique_senders_by_scope.setdefault(signal.recipient_scope, set()).add(signal.sender)

        for rule in self.graph.quorum_rules.values():
            scope_count = counts_by_scope.get(rule.target_scope, 0)
            participant_count = len(unique_senders_by_scope.get(rule.target_scope, set()))
            required_votes = max(1, math.ceil(rule.min_participants * rule.threshold))
            if scope_count >= required_votes and participant_count >= rule.min_participants:
                signal_id = f"quorum:{rule.rule_id}:{scope_count}"
                self._record_event(
                    "QUORUM_TRIGGERED",
                    step=0 if not pending_signals else self._current_step_from_signal(pending_signals[0]),
                    signal_id=signal_id,
                    details={
                        "rule_id": rule.rule_id,
                        "target_scope": rule.target_scope,
                        "scope_count": scope_count,
                        "participants": participant_count,
                    },
                )
                quorum_signals.append(
                    SignalEnvelope(
                        signal_id=signal_id,
                        mode=SignalMode.QUORUM,
                        sender="quorum_engine",
                        recipient_scope=rule.target_scope,
                        payload={
                            "rule_id": rule.rule_id,
                            "metric": rule.metric,
                            "scope_count": scope_count,
                            "participants": participant_count,
                            "action": rule.action,
                        },
                        priority=PriorityLevel.HIGH,
                        trace_path=["quorum_engine"],
                        policy_tags=[f"quorum:{rule.rule_id}"],
                    )
                )
        return quorum_signals

    def _advance_complex_lifecycle(
        self,
        *,
        active_node_ids: list[str],
        updated_channels: list[str],
    ) -> None:
        active_set = set(active_node_ids)
        updated_set = set(updated_channels)
        for compiled_complex in self.graph.complexes.values():
            members = set(compiled_complex.spec.members)
            if compiled_complex.state == ComplexLifecycleState.PENDING and active_set.intersection(members):
                compiled_complex.state = ComplexLifecycleState.ACTIVE
                self._record_event(
                    "COMPLEX_FORMED",
                    step=0,
                    details={
                        "scaffold_id": compiled_complex.scaffold_id,
                        "members": sorted(members),
                        "state": compiled_complex.state.value,
                    },
                )
            elif compiled_complex.state == ComplexLifecycleState.ACTIVE:
                if members and members.issubset(active_set):
                    shared_channel = compiled_complex.spec.shared_state_channel
                    if shared_channel is None or shared_channel in updated_set:
                        compiled_complex.state = ComplexLifecycleState.COMPLETED

    def _update_graph_state(self, state: Any, updates: dict[str, list[Any]]) -> Any:
        if not isinstance(state, dict):
            return state
        new_state = deepcopy(state)
        for channel_name, values in updates.items():
            if values:
                new_state[channel_name] = deepcopy(values[-1])
        return new_state

    def _create_snapshot(
        self,
        *,
        step: int,
        state: Any,
        pending_signals: list[SignalEnvelope],
        active_nodes: list[str],
        updated_channels: list[str],
        context: dict[str, Any],
    ) -> StateSnapshot:
        snapshot = StateSnapshot(
            snapshot_id=self._next_snapshot_id(),
            step=step,
            state=deepcopy(state),
            channel_values={
                name: deepcopy(channel.read()) for name, channel in self.graph.channels.items()
            },
            pending_signals=[deepcopy(signal) for signal in pending_signals],
            active_nodes=list(active_nodes),
            updated_channels=list(updated_channels),
            complex_states={
                scaffold_id: compiled.state
                for scaffold_id, compiled in self.graph.complexes.items()
            },
            metadata={
                "context": deepcopy(context),
            },
        )
        return snapshot

    def _next_snapshot_id(self) -> str:
        self._snapshot_counter += 1
        return f"checkpoint-{self._snapshot_counter:04d}"

    def _record_event(
        self,
        event_type_name: str,
        *,
        step: int,
        node_id: str | None = None,
        signal_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        if self.trace_recorder is None:
            return
        from bca2p.observability import RuntimeEventType

        self.trace_recorder.record_event(
            RuntimeEventType[event_type_name],
            step=step,
            node_id=node_id,
            signal_id=signal_id,
            details=details,
        )

    def _current_step_from_signal(self, signal: SignalEnvelope) -> int:
        if signal.trace_path and signal.trace_path[-1].startswith("step:"):
            try:
                return int(signal.trace_path[-1].split(":", 1)[1])
            except ValueError:
                return 0
        return 0
