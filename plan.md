# bca2p Dataset, Gemini Agent, and Benchmark Plan

## Summary

The showcase uses both public datasets and Gemini agents. Public datasets provide
repeatable ground truth; Gemini powers domain agents that reason, coordinate,
escalate, and explain. The benchmark tests whether bca2p improves communication
quality compared with generic multi-agent messaging while keeping the model,
task inputs, agent roles, and success criteria identical.

Core claim:

> bca2p does not make agents smarter by itself. It makes multi-agent systems more
> reliable by giving communication typed receptors, scoped signal modes, quorum
> gates, replay, causal feedback, and homeostatic damping.

## Tracks

- Deterministic track: no LLM dependency, CI-friendly fixtures, deterministic
  scoring, and public leaderboard output.
- Gemini track: Gemini-powered agents over the same scenario specs, with all
  leaderboard scoring still computed by deterministic metrics rather than an LLM
  judge.
- Dataset track: public or synthetic datasets are used as ground-truth sources
  for domain scenarios; v1 fixtures are small slices or simulators so the repo
  does not vendor large datasets.

## Gemini Plan

- Default agent model: `gemini-2.5-flash`.
- Optional analysis model: `gemini-2.5-pro` or newer Gemini Pro for qualitative
  reports only.
- API key source: `GEMINI_API_KEY`.
- The repo ignores `.env` and `.env.*`; keys must not be committed.
- Gemini outputs should be structured JSON that can be converted into bca2p
  signal payloads.
- Function calling should be limited to controlled tools such as
  `retrieve_evidence`, `score_alert`, `fetch_patient_context`,
  `lookup_contract_clause`, and `inspect_topology`.
- The implementation includes `examples/benchmarks/gemini.py` as the optional
  live Gemini adapter; deterministic benchmarks remain the default.

## Implemented Benchmark Surface

- `examples/benchmarks/scenarios.py`: nine risk-sensitive scenario specs.
- `examples/benchmarks/scoring.py`: deterministic weighted score from 0-100.
- `examples/benchmarks/runners.py`: baseline and bca2p runners.
- `examples/benchmarks/app.py`: CLI for JSON/Markdown output and report writes.
- `leaderboard.md`: generated public score table.
- `reports/benchmark_summary.md`: generated scenario-level comparison summary.

## Use-Case Coverage

The benchmark covers clinical escalation, cyber incident response, financial
risk surveillance, research synthesis, infrastructure operations, legal and
compliance review, supply-chain anomaly response, robotics/swarm coordination,
and emergency response.

## Evaluation Rule

No leaderboard score may depend on an LLM judge. Gemini may generate agent
decisions and narrative reports, but task correctness, routing precision,
efficiency, escalation quality, stability, replayability, and causal usefulness
are scored by deterministic code.

## Reproduce

```bash
PYTHONPATH=src python3 examples/benchmarks/app.py --format markdown
```

To regenerate the checked-in benchmark artifacts:

```bash
PYTHONPATH=src python3 examples/benchmarks/app.py --write-reports
```

## Sources

- bca2p site: https://bca2p.gitdate.ink
- bca2p use cases: https://bca2p.gitdate.ink/use-cases
- bca2p architecture: https://bca2p.gitdate.ink/architecture
- Gemini models: https://ai.google.dev/gemini-api/docs/models
- Gemini API keys: https://ai.google.dev/gemini-api/docs/api-key
- Gemini structured outputs: https://ai.google.dev/gemini-api/docs/structured-output
- Gemini function calling: https://ai.google.dev/gemini-api/docs/function-calling
