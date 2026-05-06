"""Diagnostic helpers for communication-aware observability."""

from __future__ import annotations

from collections import Counter
from typing import Any

from bca2p.graph import CompiledBioGraph

from .models import RuntimeEvent, RuntimeEventType


def detect_bottlenecks(events: list[RuntimeEvent], *, min_deliveries: int = 2) -> list[dict[str, Any]]:
    delivery_counts = Counter(
        event.node_id
        for event in events
        if event.event_type == RuntimeEventType.SIGNAL_DELIVERED and event.node_id is not None
    )
    return [
        {"node_id": node_id, "deliveries": deliveries}
        for node_id, deliveries in delivery_counts.items()
        if deliveries >= min_deliveries
    ]


def noisy_sender_report(events: list[RuntimeEvent], *, min_emits: int = 2) -> list[dict[str, Any]]:
    emit_counts = Counter(
        event.details.get("sender")
        for event in events
        if event.event_type == RuntimeEventType.SIGNAL_EMITTED and event.details.get("sender")
    )
    return [
        {"sender": sender, "emits": emits}
        for sender, emits in emit_counts.items()
        if emits >= min_emits
    ]


def dormant_receptor_report(graph: CompiledBioGraph, events: list[RuntimeEvent]) -> list[dict[str, Any]]:
    observed_receptors = {
        event.details.get("receptor")
        for event in events
        if event.event_type == RuntimeEventType.SIGNAL_DELIVERED and event.details.get("receptor")
    }
    report: list[dict[str, Any]] = []
    for node_id, node in graph.nodes.items():
        dormant = [
            receptor.receptor_id
            for receptor in node.receptors
            if receptor.receptor_id not in observed_receptors
        ]
        if dormant:
            report.append({"node_id": node_id, "dormant_receptors": dormant})
    return report


def amplification_storm_report(
    events: list[RuntimeEvent],
    *,
    amplification_threshold: float = 10.0,
) -> list[dict[str, Any]]:
    storms: list[dict[str, Any]] = []
    for event in events:
        if event.event_type != RuntimeEventType.SIGNAL_EMITTED:
            continue
        amplification = event.details.get("amplification")
        if amplification is not None and amplification >= amplification_threshold:
            storms.append(
                {
                    "signal_id": event.signal_id,
                    "sender": event.details.get("sender"),
                    "amplification": amplification,
                    "step": event.step,
                }
            )
    return storms
