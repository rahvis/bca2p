# MARL Training Guide

`bca2p.marl` is the experimental learning track for communication-policy optimization.

## What It Trains

- route choice
- amplification level
- quorum threshold selection
- complex membership selection

## Architecture

- centralized trainer
- decentralized execution policy
- deterministic synthetic benchmark environment
- JSON export/import for learned policies

## Example

Run:

```bash
PYTHONPATH=src python3 examples/marl_training/app.py
```

The example should show a trained policy outperforming the baseline policy.
