"""Trace recorder and export helpers for bca2p observability."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from bca2p.graph import CompiledBioGraph

from .models import ReplayEventBundle, RuntimeEvent, RuntimeEventType, TopologySnapshot, VisualizationGraph


class TraceRecorder:
    """Captures structured runtime events and topology snapshots."""

    def __init__(self, *, trace_id: str = "trace-1") -> None:
        self.trace_id = trace_id
        self._events: list[RuntimeEvent] = []
        self._topology_timeline: list[TopologySnapshot] = []
        self._event_counter = 0

    @property
    def events(self) -> list[RuntimeEvent]:
        return list(self._events)

    @property
    def topology_timeline(self) -> list[TopologySnapshot]:
        return list(self._topology_timeline)

    def record_event(
        self,
        event_type: RuntimeEventType,
        *,
        step: int,
        node_id: str | None = None,
        signal_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> RuntimeEvent:
        self._event_counter += 1
        event = RuntimeEvent(
            event_id=f"{self.trace_id}:event:{self._event_counter:05d}",
            event_type=event_type,
            step=step,
            node_id=node_id,
            signal_id=signal_id,
            details=details or {},
        )
        self._events.append(event)
        return event

    def record_topology_snapshot(self, graph: CompiledBioGraph, *, step: int) -> TopologySnapshot:
        receptor_index = {
            node_id: [receptor.receptor_id for receptor in node.receptors]
            for node_id, node in graph.nodes.items()
        }
        scope_index = {
            node_id: list(node.scope_subscriptions)
            for node_id, node in graph.nodes.items()
        }
        topology_index = {
            node_id: list(node.topology_subscriptions)
            for node_id, node in graph.nodes.items()
        }
        active_complexes = [
            scaffold_id
            for scaffold_id, compiled in graph.complexes.items()
            if compiled.state in {"active", "completed"}
        ]
        snapshot = TopologySnapshot(
            step=step,
            node_ids=sorted(graph.nodes.keys()),
            channel_names=sorted(graph.channels.keys()),
            active_complexes=sorted(active_complexes),
            receptor_index=receptor_index,
            scope_index=scope_index,
            topology_index=topology_index,
        )
        self._topology_timeline.append(snapshot)
        return snapshot

    def build_bundle(
        self,
        *,
        checkpoint_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ReplayEventBundle:
        return ReplayEventBundle(
            trace_id=self.trace_id,
            events=self.events,
            topology_timeline=self.topology_timeline,
            checkpoint_ids=checkpoint_ids or [],
            metadata=metadata or {},
        )

    def to_json(
        self,
        *,
        checkpoint_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        indent: int = 2,
    ) -> str:
        bundle = self.build_bundle(checkpoint_ids=checkpoint_ids, metadata=metadata)
        return json.dumps(bundle.to_dict(), indent=indent, sort_keys=True)

    def export_json(
        self,
        path: str | Path,
        *,
        checkpoint_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        indent: int = 2,
    ) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            self.to_json(checkpoint_ids=checkpoint_ids, metadata=metadata, indent=indent),
            encoding="utf-8",
        )
        return target

    def build_visualization_graph(self) -> VisualizationGraph:
        node_ids: set[str] = set()
        edges: list[dict[str, Any]] = []

        for event in self._events:
            if event.node_id is not None:
                node_ids.add(event.node_id)
            if event.event_type == RuntimeEventType.SIGNAL_EMITTED:
                sender = event.details.get("sender")
                if sender:
                    node_ids.add(sender)
                edges.append(
                    {
                        "source": sender,
                        "target": event.details.get("recipient_scope"),
                        "kind": event.event_type.value,
                        "signal_id": event.signal_id,
                    }
                )
            elif event.event_type == RuntimeEventType.SIGNAL_DELIVERED:
                sender = event.details.get("sender")
                target = event.node_id
                if sender:
                    node_ids.add(sender)
                if target:
                    node_ids.add(target)
                edges.append(
                    {
                        "source": sender,
                        "target": target,
                        "kind": event.event_type.value,
                        "signal_id": event.signal_id,
                    }
                )

        nodes = [{"id": node_id} for node_id in sorted(node_ids)]
        annotations = {
            "event_counts": {
                event_type.value: len(
                    [event for event in self._events if event.event_type == event_type]
                )
                for event_type in RuntimeEventType
            }
        }
        return VisualizationGraph(nodes=nodes, edges=edges, annotations=annotations)
