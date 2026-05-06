from __future__ import annotations

from bca2p.core import SignalMode
from bca2p.sim import CascadeModel, Cell, CellWorld, Ligand, Receptor


def test_signaling_modes_route_distinctly() -> None:
    world = CellWorld()
    world.add_cell(
        Cell(
            cell_id="a",
            compartment="comp-1",
            neighbors=["b"],
            contacts=["b"],
            synapses=["c"],
            receptors=[
                Receptor(
                    receptor_id="r-a",
                    ligand_name="x",
                    accepted_modes=(SignalMode.AUTOCRINE, SignalMode.PARACRINE),
                    cascade_model=CascadeModel(cascade_id="a", amplification_gain=1.5),
                )
            ],
        )
    )
    world.add_cell(
        Cell(
            cell_id="b",
            compartment="comp-1",
            receptors=[
                Receptor(
                    receptor_id="r-b",
                    ligand_name="x",
                    accepted_modes=(SignalMode.PARACRINE, SignalMode.JUXTACRINE),
                )
            ],
        )
    )
    world.add_cell(
        Cell(
            cell_id="c",
            compartment="comp-2",
            receptors=[
                Receptor(
                    receptor_id="r-c",
                    ligand_name="x",
                    accepted_modes=(SignalMode.ENDOCRINE, SignalMode.SYNAPTIC),
                )
            ],
        )
    )

    world.emit(
        Ligand(
            ligand_id="auto",
            ligand_name="x",
            mode=SignalMode.AUTOCRINE,
            source_cell_id="a",
            concentration=1.0,
        )
    )
    world.emit(
        Ligand(
            ligand_id="endo",
            ligand_name="x",
            mode=SignalMode.ENDOCRINE,
            source_cell_id="a",
            concentration=1.0,
        )
    )
    snapshot = world.step()

    auto_event = next(event for event in snapshot.delivered_events if event.ligand_id == "auto")
    endo_event = next(event for event in snapshot.delivered_events if event.ligand_id == "endo")

    assert auto_event.target_cell_ids == ["a"]
    assert set(endo_event.target_cell_ids) == {"a", "b", "c"}
    assert snapshot.internal_state["a"]["r-a"] > 0.0


def test_feedback_and_amplification_accumulate_signal_state() -> None:
    world = CellWorld()
    world.add_cell(
        Cell(
            cell_id="a",
            compartment="comp-1",
            receptors=[
                Receptor(
                    receptor_id="r-a",
                    ligand_name="x",
                    accepted_modes=(SignalMode.AUTOCRINE,),
                    cascade_model=CascadeModel(
                        cascade_id="feedback",
                        amplification_gain=2.0,
                        feedback_gain=0.5,
                        decay=0.0,
                    ),
                )
            ],
        )
    )
    world.emit(
        Ligand(
            ligand_id="1",
            ligand_name="x",
            mode=SignalMode.AUTOCRINE,
            source_cell_id="a",
            concentration=1.0,
            ttl_steps=2,
        )
    )
    first = world.step()
    world.emit(
        Ligand(
            ligand_id="2",
            ligand_name="x",
            mode=SignalMode.AUTOCRINE,
            source_cell_id="a",
            concentration=1.0,
        )
    )
    second = world.step()

    assert second.internal_state["a"]["r-a"] > first.internal_state["a"]["r-a"]
