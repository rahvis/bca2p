# `bca2p`

`bca2p` is a Python SDK for bio-inspired agent-to-agent communication. It is designed to layer typed signaling, causal feedback, scoped communication, and adaptive topology on top of modern agent frameworks such as LangGraph and LangChain, while also supporting a native runtime path.

## Status

The repository now includes the stable V1 platform path plus experimental research tracks described in `prd.md` and `agent.md`.

Implemented layers:

- typed protocol models
- graph authoring and channels
- stable runtime and checkpointing
- causal learning and observability
- registry, transport, and A2A bridge
- LangGraph and LangChain integrations
- native runtime
- experimental MARL trainer
- experimental cell-signaling simulator
- experimental distributed substrate

## Package Layout

```text
src/bca2p/
  core/            # Public protocol objects and schemas
  graph/           # Graph builder and channels
  runtime/         # Stable local runtime
  learning/        # Causal inference and policy updates
  transport/       # Local/remote transports and A2A bridge
  registry/        # Agent and receptor discovery
  observability/   # Traces, replay, diagnostics
  integrations/    # LangGraph and LangChain adapters
  native/          # Experimental native runtime
  marl/            # Experimental communication training
  sim/             # Experimental biology-faithful simulation
  distributed/     # Experimental distributed substrate
```

## Python Support

- Primary target: Python `3.13.x`
- Secondary target: Python `3.14.x`

The local workstation may use Python `3.14`, but the package metadata and tooling are configured around a `3.13` baseline for SDK stability.

## Developer Tooling

- `ruff` for linting and formatting
- `pyright` for static typing
- `pytest` and `pytest-asyncio` for tests
- `pre-commit` for local quality gates

## Quick Start

Create a virtual environment with Python `3.13`, then install the package in editable mode with development dependencies:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run local checks:

```bash
ruff check .
ruff format --check .
pyright
pytest
```

## Repository Documents

- Product definition: [prd.md](./prd.md)
- Implementation plan: [agent.md](./agent.md)
- Architecture docs: [docs/architecture/README.md](./docs/architecture/README.md)
- API docs index: [docs/api/README.md](./docs/api/README.md)
- Guides index: [docs/guides/README.md](./docs/guides/README.md)
- Changelog: [CHANGELOG.md](./CHANGELOG.md)
