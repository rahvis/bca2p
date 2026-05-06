"""Agent registry and receptor discovery helpers."""

from __future__ import annotations

from dataclasses import dataclass

from bca2p.core import AgentProfile

from .store import InMemoryRegistryStore, RegistryStore


@dataclass
class AgentRegistry:
    """Registry facade for agent profiles and receptor discovery."""

    store: RegistryStore | None = None

    def __post_init__(self) -> None:
        if self.store is None:
            self.store = InMemoryRegistryStore()

    def register(self, profile: AgentProfile) -> AgentProfile:
        self.store.save(profile)
        return profile

    def get(self, agent_id: str) -> AgentProfile | None:
        return self.store.get(agent_id)

    def list(self) -> list[AgentProfile]:
        return self.store.list()

    def receptor_catalog(self) -> dict[str, list[str]]:
        catalog: dict[str, list[str]] = {}
        for profile in self.list():
            catalog[profile.agent_id] = [receptor.receptor_id for receptor in profile.receptors]
        return catalog

    def find_by_receptor(self, receptor_id: str) -> list[AgentProfile]:
        return [
            profile
            for profile in self.list()
            if any(receptor.receptor_id == receptor_id for receptor in profile.receptors)
        ]

    def find_by_scope(self, scope: str) -> list[AgentProfile]:
        return [
            profile
            for profile in self.list()
            if scope in profile.scopes
        ]
