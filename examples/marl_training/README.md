# MARL Training Example

This example demonstrates the experimental communication-policy trainer in `bca2p.marl`.

It uses a deterministic synthetic environment where the planner must learn:

- route choice
- amplification level
- quorum threshold selection
- complex membership choice

Run it with:

```bash
PYTHONPATH=src python3 examples/marl_training/app.py
```

Expected outcome:

- the trained policy outperforms the static baseline on average reward
- the learned policy is exported to `examples/marl_training/artifacts/policy.json`
