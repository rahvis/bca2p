from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for _path in (ROOT, SRC):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)

from bca2p.core import SignalMode
from bca2p.sim import CascadeModel, Cell, CellWorld, Ligand, Receptor


def run_cell_simulation_example() -> dict:
    world = CellWorld()
    world.add_cell(
        Cell(
            cell_id="cell-a",
            compartment="tissue-a",
            neighbors=["cell-b"],
            contacts=["cell-b"],
            synapses=["cell-c"],
            receptors=[
                Receptor(
                    receptor_id="egf-auto",
                    ligand_name="egf",
                    accepted_modes=(SignalMode.AUTOCRINE, SignalMode.PARACRINE),
                    cascade_model=CascadeModel(cascade_id="mapk", amplification_gain=1.4, feedback_gain=0.1),
                ),
            ],
        )
    )
    world.add_cell(
        Cell(
            cell_id="cell-b",
            compartment="tissue-a",
            receptors=[
                Receptor(
                    receptor_id="egf-para",
                    ligand_name="egf",
                    accepted_modes=(SignalMode.PARACRINE, SignalMode.JUXTACRINE),
                    cascade_model=CascadeModel(cascade_id="akt", amplification_gain=1.2),
                ),
            ],
        )
    )
    world.add_cell(
        Cell(
            cell_id="cell-c",
            compartment="tissue-b",
            receptors=[
                Receptor(
                    receptor_id="cort-endo",
                    ligand_name="cortisol",
                    accepted_modes=(SignalMode.ENDOCRINE, SignalMode.SYNAPTIC),
                    cascade_model=CascadeModel(cascade_id="stress", amplification_gain=1.1),
                ),
            ],
        )
    )

    world.emit(
        Ligand(
            ligand_id="lig-auto",
            ligand_name="egf",
            mode=SignalMode.AUTOCRINE,
            source_cell_id="cell-a",
            concentration=1.0,
        )
    )
    world.emit(
        Ligand(
            ligand_id="lig-para",
            ligand_name="egf",
            mode=SignalMode.PARACRINE,
            source_cell_id="cell-a",
            concentration=1.0,
        )
    )
    world.emit(
        Ligand(
            ligand_id="lig-endo",
            ligand_name="cortisol",
            mode=SignalMode.ENDOCRINE,
            source_cell_id="cell-a",
            concentration=1.0,
        )
    )
    snapshot = world.step()
    return {
        "step": snapshot.step,
        "events": [
            {
                "ligand_id": event.ligand_id,
                "ligand_name": event.ligand_name,
                "mode": event.mode.value,
                "source_cell_id": event.source_cell_id,
                "target_cell_ids": list(event.target_cell_ids),
                "concentration": event.concentration,
            }
            for event in snapshot.delivered_events
        ],
        "internal_state": snapshot.internal_state,
        "agent_mapping": {
            "autocrine": "self-reflection and local memory consolidation",
            "paracrine": "local team coordination",
            "endocrine": "global policy broadcast",
            "juxtacrine": "high-trust direct handoff",
            "synaptic": "persistent low-latency edge",
        },
    }


if __name__ == "__main__":
    print(run_cell_simulation_example())
