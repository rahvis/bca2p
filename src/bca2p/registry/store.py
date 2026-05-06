"""Registry storage backends for agent discovery."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from bca2p.core import AgentProfile


class RegistryStore(Protocol):
    """Storage interface for agent profiles."""

    def save(self, profile: AgentProfile) -> None:
        """Persist a profile."""

    def get(self, agent_id: str) -> AgentProfile | None:
        """Return a profile by ID."""

    def list(self) -> list[AgentProfile]:
        """Return all stored profiles."""


@dataclass
class InMemoryRegistryStore:
    """Simple in-memory registry store."""

    _profiles: dict[str, AgentProfile] | None = None

    def __post_init__(self) -> None:
        if self._profiles is None:
            self._profiles = {}

    def save(self, profile: AgentProfile) -> None:
        self._profiles[profile.agent_id] = profile

    def get(self, agent_id: str) -> AgentProfile | None:
        return self._profiles.get(agent_id)

    def list(self) -> list[AgentProfile]:
        return list(self._profiles.values())


@dataclass
class FileRegistryStore:
    """File-backed registry store using JSON serialization."""

    directory: str | Path

    def __post_init__(self) -> None:
        self._directory = Path(self.directory)
        self._directory.mkdir(parents=True, exist_ok=True)

    def _path_for(self, agent_id: str) -> Path:
        return self._directory / f"{agent_id}.json"

    def save(self, profile: AgentProfile) -> None:
        path = self._path_for(profile.agent_id)
        path.write_text(json.dumps(profile.to_dict(), indent=2, sort_keys=True), encoding="utf-8")

    def get(self, agent_id: str) -> AgentProfile | None:
        path = self._path_for(agent_id)
        if not path.exists():
            return None
        return AgentProfile.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list(self) -> list[AgentProfile]:
        profiles: list[AgentProfile] = []
        for path in sorted(self._directory.glob("*.json")):
            profiles.append(AgentProfile.from_dict(json.loads(path.read_text(encoding="utf-8"))))
        return profiles
