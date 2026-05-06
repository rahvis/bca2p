"""Checkpoint storage implementations for the stable runtime."""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .models import StateSnapshot


class Checkpointer(Protocol):
    """Protocol for checkpoint storage backends."""

    def save(self, snapshot: StateSnapshot) -> None:
        """Persist a snapshot."""

    def get(self, snapshot_id: str) -> StateSnapshot | None:
        """Return a snapshot by ID."""

    def history(self) -> list[StateSnapshot]:
        """Return snapshots in insertion order."""


@dataclass
class InMemoryCheckpointer:
    """Simple in-memory checkpoint store."""

    _snapshots: list[StateSnapshot] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self._snapshots is None:
            self._snapshots = []

    def save(self, snapshot: StateSnapshot) -> None:
        self._snapshots.append(snapshot)

    def get(self, snapshot_id: str) -> StateSnapshot | None:
        for snapshot in self._snapshots:
            if snapshot.snapshot_id == snapshot_id:
                return snapshot
        return None

    def history(self) -> list[StateSnapshot]:
        return list(self._snapshots)


@dataclass
class FileCheckpointer:
    """Local file-backed checkpoint store using pickle serialization."""

    directory: str | Path

    def __post_init__(self) -> None:
        self._directory = Path(self.directory)
        self._directory.mkdir(parents=True, exist_ok=True)

    def _path_for(self, snapshot_id: str) -> Path:
        return self._directory / f"{snapshot_id}.pkl"

    def save(self, snapshot: StateSnapshot) -> None:
        with self._path_for(snapshot.snapshot_id).open("wb") as handle:
            pickle.dump(snapshot, handle)

    def get(self, snapshot_id: str) -> StateSnapshot | None:
        path = self._path_for(snapshot_id)
        if not path.exists():
            return None
        with path.open("rb") as handle:
            return pickle.load(handle)

    def history(self) -> list[StateSnapshot]:
        snapshots: list[StateSnapshot] = []
        for path in sorted(self._directory.glob("*.pkl")):
            with path.open("rb") as handle:
                snapshots.append(pickle.load(handle))
        return snapshots
