# Distributed Substrate Guide

`bca2p.distributed` provides the experimental SDK-owned substrate for remote coordination.

## Core Components

- registry store
- topology index
- signal log
- artifact store
- mesh transport

## Why It Exists

This layer allows remote coordination without requiring LangGraph or LangChain infrastructure.

## Failure and Replay

The substrate supports:

- dropped-node simulation
- partition simulation
- persisted signal logs
- replay after restart

## Example

Run:

```bash
PYTHONPATH=src python3 examples/distributed_mesh/app.py
```
