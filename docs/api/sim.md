# `bca2p.sim`

Experimental biology-faithful signaling simulation layer.

## Main Objects

- `CellWorld`
- `Cell`
- `Ligand`
- `Receptor`
- `DiffusionField`
- `CascadeModel`
- `CellSignalEvent`
- `CellWorldSnapshot`

## Scope

This module models simplified:

- autocrine signaling
- paracrine signaling
- endocrine signaling
- juxtacrine signaling
- synaptic signaling
- intracellular amplification and feedback

It is intended for validating communication abstractions, not for high-fidelity wet-lab simulation.
