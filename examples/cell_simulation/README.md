# Cell Simulation Example

This example demonstrates the experimental signaling simulator in `bca2p.sim`.

It creates a small multi-compartment cell world and exercises:

- autocrine signaling
- paracrine signaling
- endocrine signaling
- intracellular cascade amplification

Run it with:

```bash
PYTHONPATH=src python3 examples/cell_simulation/app.py
```

The output includes a biology-to-agent mapping showing how each signaling family translates into agent communication semantics.
