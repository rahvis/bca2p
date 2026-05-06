# Cell Simulation Guide

`bca2p.sim` validates the biology-to-agent mapping using a simplified signaling world.

## Supported Modes

- autocrine
- paracrine
- endocrine
- juxtacrine
- synaptic

## What Is Modeled

- ligand emission
- compartment-aware diffusion
- receptor binding
- intracellular amplification
- feedback accumulation

## Example

Run:

```bash
PYTHONPATH=src python3 examples/cell_simulation/app.py
```

Use the resulting activation map to compare biological signaling semantics to agent communication design choices.
