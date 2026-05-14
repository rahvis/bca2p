# bca2p Coordination Benchmark Spec

## Goal

Measure whether bca2p improves multi-agent communication behavior over generic
agent messaging in risk-sensitive domains.

The benchmark isolates communication mechanics. Baseline and bca2p approaches
use the same scenario, task input, agent roles, and ground-truth answer.

## Approaches

### Baseline Generic Agents

- Plain messages or broad fan-out.
- Same agent roles as bca2p.
- Escalation decided by prompt logic or simple orchestration.
- Ordinary transcript-style logs.
- No typed receptors, scoped signal modes, quorum gate, replay bundle, or causal
  feedback graph.

### bca2p Agents

- Communication wrapped in `SignalEnvelope`.
- Agents expose receptor contracts with `ReceptorSpec`.
- Local/global/direct/artifact communication uses `SignalMode`.
- Escalation is represented with `QuorumRule`.
- Noisy routing is damped by `HomeostasisPolicy`.
- Replay and event lineage are captured with `TraceRecorder`.
- Outcome attribution is recorded with `CausalGraphStore`.

## Agent Pattern

Each scenario uses this pattern:

- Detector agents convert dataset events into typed candidate signals.
- Specialist agents inspect domain evidence.
- Risk agents estimate severity and confidence.
- Coordinator agents keep signals local, form a temporary complex, or escalate.
- Action agents recommend containment, routing, dispatch, remediation, review, or
  approval.
- Audit agents produce replayable explanation packets.

## Metrics

Scores are 0-100 and use deterministic code in
`examples/benchmarks/scoring.py`.

| Metric | Weight | Meaning |
|---|---:|---|
| Task correctness | 30% | Correct final decision against ground truth. |
| Routing precision | 15% | Relevant deliveries divided by all deliveries. |
| Communication efficiency | 15% | Lower message, duplicate work, token, and latency pressure. |
| Escalation quality | 15% | Correct escalation timing without false or missed escalations. |
| Stability | 10% | Fewer retry storms, route flaps, and amplification events. |
| Replayability | 10% | Presence of replay artifacts, evidence artifacts, and quorum state. |
| Causal usefulness | 5% | Presence of causal links and structured feedback records. |

## Acceptance Criteria

- All nine scenarios must run from `examples/benchmarks/app.py`.
- bca2p must outperform baseline in every deterministic v1 scenario.
- The generated leaderboard must include scenario, dataset, baseline score,
  bca2p score, score delta, and strongest claim.
- The default run must not require Gemini, dataset downloads, or API keys.
- The optional Gemini track must read `GEMINI_API_KEY` only at runtime.
- `.env` and `.env.*` must remain ignored.

## Commands

Run Markdown leaderboard:

```bash
PYTHONPATH=src python3 examples/benchmarks/app.py --format markdown
```

Run JSON output:

```bash
PYTHONPATH=src python3 examples/benchmarks/app.py --format json
```

Regenerate artifacts:

```bash
PYTHONPATH=src python3 examples/benchmarks/app.py --write-reports
```
