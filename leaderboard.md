# bca2p Coordination Benchmark Leaderboard

This leaderboard is generated from deterministic benchmark fixtures. Scores are 0-100 and do not depend on an LLM judge.

| Rank | Use case | Dataset | Baseline | bca2p | Delta | Claim |
|---:|---|---|---:|---:|---:|---|
| 1 | Cyber incident response | CIC-IDS2017 | 21.09 | 92.76 | 71.67 | largest gain: task correctness |
| 2 | Financial risk surveillance | IBM synthetic AML transactions | 50.77 | 92.63 | 41.86 | largest gain: causal usefulness |
| 3 | Clinical escalation and care coordination | Synthea synthetic patient data | 60.92 | 92.12 | 31.20 | largest gain: causal usefulness |
| 4 | Emergency response and disaster operations | CrisisMMD | 52.06 | 91.91 | 39.85 | largest gain: causal usefulness |
| 5 | Autonomous research and evidence synthesis | FEVER | 62.20 | 91.05 | 28.85 | largest gain: causal usefulness |
| 6 | Legal and compliance review | CUAD | 61.20 | 90.75 | 29.55 | largest gain: causal usefulness |
| 7 | Autonomous infrastructure operations | Alibaba Cluster Trace Program | 13.34 | 90.41 | 77.07 | largest gain: task correctness |
| 8 | Supply-chain anomaly response | M5 Walmart forecasting dataset | 17.71 | 89.95 | 72.24 | largest gain: task correctness |
| 9 | Robotics and swarm coordination | PettingZoo MPE / MPE2 | 11.17 | 89.95 | 78.78 | largest gain: task correctness |

## Aggregate

- Average baseline score: 38.94
- Average bca2p score: 91.28
- Average improvement: 52.34

## Reproduce

```bash
PYTHONPATH=src python3 examples/benchmarks/app.py --format markdown
```
