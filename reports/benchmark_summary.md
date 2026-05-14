# bca2p Coordination Benchmark Summary

The deterministic benchmark isolates communication mechanics from model quality. Each scenario compares plain multi-agent messaging with bca2p typed signaling under the same use case, agent roles, task input, and ground-truth decision.

## Clinical escalation and care coordination

- Dataset: Synthea synthetic patient data
- Ground truth: Escalate deteriorating patient only after specialist confidence converges.
- Baseline score: 60.92
- bca2p score: 92.12
- Delta: 31.20
- Strongest claim: largest gain: causal usefulness

## Cyber incident response

- Dataset: CIC-IDS2017
- Ground truth: Contain only after independent network, endpoint, and identity evidence converges.
- Baseline score: 21.09
- bca2p score: 92.76
- Delta: 71.67
- Strongest claim: largest gain: task correctness

## Financial risk surveillance

- Dataset: IBM synthetic AML transactions
- Ground truth: Escalate suspicious activity with independent transaction and account evidence.
- Baseline score: 50.77
- bca2p score: 92.63
- Delta: 41.86
- Strongest claim: largest gain: causal usefulness

## Autonomous research and evidence synthesis

- Dataset: FEVER
- Ground truth: Synthesize only supported claims and preserve evidence lineage.
- Baseline score: 62.20
- bca2p score: 91.05
- Delta: 28.85
- Strongest claim: largest gain: causal usefulness

## Autonomous infrastructure operations

- Dataset: Alibaba Cluster Trace Program
- Ground truth: Remediate degraded services without retry storms or blast-radius expansion.
- Baseline score: 13.34
- bca2p score: 90.41
- Delta: 77.07
- Strongest claim: largest gain: task correctness

## Legal and compliance review

- Dataset: CUAD
- Ground truth: Approve high-risk clauses only after legal, policy, and business convergence.
- Baseline score: 61.20
- bca2p score: 90.75
- Delta: 29.55
- Strongest claim: largest gain: causal usefulness

## Supply-chain anomaly response

- Dataset: M5 Walmart forecasting dataset
- Ground truth: Reroute inventory after sustained local disruption, not isolated demand noise.
- Baseline score: 17.71
- bca2p score: 89.95
- Delta: 72.24
- Strongest claim: largest gain: task correctness

## Robotics and swarm coordination

- Dataset: PettingZoo MPE / MPE2
- Ground truth: Change formation only after local hazard quorum while preserving pair links.
- Baseline score: 11.17
- bca2p score: 89.95
- Delta: 78.78
- Strongest claim: largest gain: task correctness

## Emergency response and disaster operations

- Dataset: CrisisMMD
- Ground truth: Broadcast global directives only after confirmed local emergency evidence.
- Baseline score: 52.06
- bca2p score: 91.91
- Delta: 39.85
- Strongest claim: largest gain: causal usefulness
