"""Channel abstractions for the bca2p graph layer."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable


def _deduplicate_preserve_order(values: Iterable[Any]) -> list[Any]:
    result: list[Any] = []
    seen: set[str] = set()
    for value in values:
        marker = repr(value)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(value)
    return result


@dataclass
class BaseChannel:
    """Base channel contract for graph-local state exchange."""

    name: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def apply_updates(self, updates: list[Any]) -> Any:
        raise NotImplementedError

    def read(self) -> Any:
        raise NotImplementedError

    def clone(self) -> "BaseChannel":
        return deepcopy(self)


@dataclass
class LastValueChannel(BaseChannel):
    """Stores the most recent update applied to the channel."""

    value: Any = None

    def apply_updates(self, updates: list[Any]) -> Any:
        if updates:
            self.value = updates[-1]
        return self.value

    def read(self) -> Any:
        return self.value


@dataclass
class TopicChannel(BaseChannel):
    """Collects a sequence of updates, optionally deduplicating them."""

    value: list[Any] = field(default_factory=list)
    accumulate: bool = True
    deduplicate: bool = False

    def apply_updates(self, updates: list[Any]) -> list[Any]:
        values = list(updates)
        if self.deduplicate:
            values = _deduplicate_preserve_order(values)

        if self.accumulate:
            self.value.extend(values)
            if self.deduplicate:
                self.value = _deduplicate_preserve_order(self.value)
        else:
            self.value = values
        return list(self.value)

    def read(self) -> list[Any]:
        return list(self.value)


@dataclass
class AggregateChannel(BaseChannel):
    """Aggregates updates using a reducer function."""

    reducer: Callable[[Any, Any], Any] = lambda left, right: right
    initial_value: Any = None
    value: Any = None

    def __post_init__(self) -> None:
        if self.value is None:
            self.value = deepcopy(self.initial_value)

    def apply_updates(self, updates: list[Any]) -> Any:
        current = self.value
        for update in updates:
            current = self.reducer(current, update)
        self.value = current
        return self.value

    def read(self) -> Any:
        return self.value


@dataclass
class EphemeralChannel(BaseChannel):
    """Stores the most recent update batch until explicitly reset."""

    value: Any = None

    def apply_updates(self, updates: list[Any]) -> Any:
        self.value = updates[-1] if updates else None
        return self.value

    def read(self) -> Any:
        return self.value

    def reset(self) -> None:
        self.value = None
