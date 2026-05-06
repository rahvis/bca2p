"""Experimental biology-faithful signaling simulation primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from bca2p.core import SignalMode


@dataclass(slots=True)
class CascadeModel:
    """Simplified intracellular cascade model with amplification and feedback."""

    cascade_id: str
    amplification_gain: float = 1.0
    feedback_gain: float = 0.0
    decay: float = 0.1

    def activate(self, concentration: float, previous_state: float) -> float:
        amplified = concentration * self.amplification_gain
        feedback = previous_state * self.feedback_gain
        retained = previous_state * max(0.0, 1.0 - self.decay)
        return retained + amplified + feedback


@dataclass(slots=True)
class Receptor:
    """Simplified receptor model bound to a ligand family and signal modes."""

    receptor_id: str
    ligand_name: str
    accepted_modes: tuple[SignalMode, ...]
    affinity: float = 1.0
    cascade_model: CascadeModel = field(
        default_factory=lambda: CascadeModel(cascade_id="default-cascade")
    )

    def responds_to(self, ligand_name: str, mode: SignalMode) -> bool:
        return self.ligand_name == ligand_name and mode in self.accepted_modes


@dataclass(slots=True)
class Ligand:
    """Extracellular signaling payload emitted by a cell."""

    ligand_id: str
    ligand_name: str
    mode: SignalMode
    source_cell_id: str
    concentration: float
    target_scope: str | None = None
    target_cells: tuple[str, ...] = ()
    ttl_steps: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Cell:
    """Cell with receptors, compartments, adjacency, and internal messenger state."""

    cell_id: str
    compartment: str
    receptors: list[Receptor] = field(default_factory=list)
    neighbors: list[str] = field(default_factory=list)
    contacts: list[str] = field(default_factory=list)
    synapses: list[str] = field(default_factory=list)
    internal_state: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DiffusionField:
    """Tracks extracellular concentrations per cell and compartment."""

    per_cell: dict[str, dict[str, float]] = field(default_factory=dict)
    per_compartment: dict[str, dict[str, float]] = field(default_factory=dict)

    def add_to_cell(self, cell_id: str, ligand_name: str, concentration: float) -> None:
        self.per_cell.setdefault(cell_id, {})
        self.per_cell[cell_id][ligand_name] = (
            self.per_cell[cell_id].get(ligand_name, 0.0) + concentration
        )

    def add_to_compartment(self, compartment: str, ligand_name: str, concentration: float) -> None:
        self.per_compartment.setdefault(compartment, {})
        self.per_compartment[compartment][ligand_name] = (
            self.per_compartment[compartment].get(ligand_name, 0.0) + concentration
        )

    def concentration_for(self, cell: Cell, ligand_name: str) -> float:
        local = self.per_cell.get(cell.cell_id, {}).get(ligand_name, 0.0)
        compartment = self.per_compartment.get(cell.compartment, {}).get(ligand_name, 0.0)
        return local + compartment

    def reset(self) -> None:
        self.per_cell.clear()
        self.per_compartment.clear()


@dataclass(slots=True)
class CellSignalEvent:
    """One emitted and routed signaling event inside the simulated world."""

    ligand_id: str
    ligand_name: str
    mode: SignalMode
    source_cell_id: str
    target_cell_ids: list[str]
    concentration: float


@dataclass(slots=True)
class CellWorldSnapshot:
    """Serializable state snapshot after a simulation step."""

    step: int
    internal_state: dict[str, dict[str, float]]
    diffusion_field: dict[str, Any]
    delivered_events: list[CellSignalEvent] = field(default_factory=list)


@dataclass(slots=True)
class CellWorld:
    """Research-usable simulation world for signaling-mode validation."""

    cells: dict[str, Cell] = field(default_factory=dict)
    diffusion_field: DiffusionField = field(default_factory=DiffusionField)
    systemic_attenuation: float = 0.7
    local_decay: float = 0.2
    step_count: int = 0
    _pending_ligands: list[Ligand] = field(default_factory=list)
    _last_events: list[CellSignalEvent] = field(default_factory=list)

    def add_cell(self, cell: Cell) -> Cell:
        self.cells[cell.cell_id] = cell
        return cell

    def emit(self, ligand: Ligand) -> Ligand:
        self._pending_ligands.append(ligand)
        return ligand

    def step(self) -> CellWorldSnapshot:
        self.step_count += 1
        self.diffusion_field.reset()
        self._last_events = []
        for ligand in list(self._pending_ligands):
            self._route_ligand(ligand)
        self._apply_cascades()
        self._pending_ligands = [
            ligand for ligand in self._pending_ligands if ligand.ttl_steps > 1
        ]
        for ligand in self._pending_ligands:
            ligand.ttl_steps -= 1
        return self.snapshot()

    def snapshot(self) -> CellWorldSnapshot:
        return CellWorldSnapshot(
            step=self.step_count,
            internal_state={
                cell_id: dict(cell.internal_state)
                for cell_id, cell in self.cells.items()
            },
            diffusion_field={
                "per_cell": {
                    cell_id: dict(values)
                    for cell_id, values in self.diffusion_field.per_cell.items()
                },
                "per_compartment": {
                    compartment: dict(values)
                    for compartment, values in self.diffusion_field.per_compartment.items()
                },
            },
            delivered_events=list(self._last_events),
        )

    def _route_ligand(self, ligand: Ligand) -> None:
        source = self.cells[ligand.source_cell_id]
        target_ids: list[str]
        if ligand.mode == SignalMode.AUTOCRINE:
            target_ids = [source.cell_id]
        elif ligand.mode == SignalMode.PARACRINE:
            target_ids = [
                cell_id
                for cell_id, cell in self.cells.items()
                if cell.compartment == source.compartment
                and cell_id in set(source.neighbors + [source.cell_id])
            ]
        elif ligand.mode == SignalMode.ENDOCRINE:
            target_ids = sorted(self.cells.keys())
        elif ligand.mode == SignalMode.JUXTACRINE:
            target_ids = list(source.contacts or ligand.target_cells)
        elif ligand.mode == SignalMode.SYNAPTIC:
            target_ids = list(source.synapses or ligand.target_cells)
        else:
            target_ids = list(ligand.target_cells)

        if ligand.mode == SignalMode.ENDOCRINE:
            concentration = ligand.concentration * self.systemic_attenuation
        elif ligand.mode == SignalMode.PARACRINE:
            concentration = ligand.concentration * (1.0 - self.local_decay)
        else:
            concentration = ligand.concentration

        self._last_events.append(
            CellSignalEvent(
                ligand_id=ligand.ligand_id,
                ligand_name=ligand.ligand_name,
                mode=ligand.mode,
                source_cell_id=ligand.source_cell_id,
                target_cell_ids=target_ids,
                concentration=concentration,
            )
        )

        for target_id in target_ids:
            target = self.cells[target_id]
            self.diffusion_field.add_to_cell(target_id, ligand.ligand_name, concentration)
            self.diffusion_field.add_to_compartment(
                target.compartment,
                ligand.ligand_name,
                concentration * 0.1,
            )

    def _apply_cascades(self) -> None:
        for cell in self.cells.values():
            for receptor in cell.receptors:
                concentration = self.diffusion_field.concentration_for(cell, receptor.ligand_name)
                if concentration <= 0:
                    continue
                previous = cell.internal_state.get(receptor.receptor_id, 0.0)
                cell.internal_state[receptor.receptor_id] = receptor.cascade_model.activate(
                    concentration * receptor.affinity,
                    previous,
                )
