# bca2p Coordination Benchmarks

This package contains the reproducible benchmark scaffold for showing that
`bca2p` improves multi-agent communication behavior over generic agent
messaging.

Run the deterministic benchmark:

```bash
PYTHONPATH=src python3 examples/benchmarks/app.py --format markdown
```

Write generated artifacts:

```bash
PYTHONPATH=src python3 examples/benchmarks/app.py --write-reports
```

The default track does not call Gemini. The optional Gemini adapter in
`gemini.py` reads `GEMINI_API_KEY` at runtime and is intended for live agent
reasoning experiments over the same scenario definitions.
