# bca2p Benchmark Datasets

The benchmark uses public or synthetic datasets as ground-truth sources. Large
datasets are not committed to this repo. Scenario fixtures should be generated
from small, documented slices and stored under a future ignored data directory or
downloaded during benchmark preparation.

| Use case | Primary dataset/simulator | Role in benchmark |
|---|---|---|
| Clinical escalation | Synthea synthetic patient data | Synthetic patient histories for deterioration and escalation scenarios. |
| Cyber incident response | CIC-IDS2017 | Labeled benign/attack flows for alert flood and containment scenarios. |
| Financial risk surveillance | IBM synthetic AML transactions | Synthetic transaction graphs with AML labels for escalation and false-positive evaluation. |
| Research/evidence synthesis | FEVER | Claim/evidence/support labels for attribution and unsupported synthesis checks. |
| Infrastructure operations | Alibaba Cluster Trace Program | Production-style resource and dependency traces for retry storm and remediation tests. |
| Legal/compliance review | CUAD | Expert-labeled contract clauses for policy routing and approval lineage. |
| Supply-chain anomaly response | M5 Walmart forecasting dataset | Retail demand hierarchy for local disruption versus global overreaction tests. |
| Robotics/swarm coordination | PettingZoo MPE / MPE2 | Multi-agent communication simulator for hazards, pair links, and formation changes. |
| Emergency response | CrisisMMD | Annotated disaster social media items for field report validation and dispatch confidence. |

## Dataset Policy

- Prefer synthetic or public benchmark data over real sensitive data.
- Do not commit raw large datasets.
- Keep each scenario fixture small enough for CI.
- Store source URL, dataset version/date, preprocessing command, seed, and
  fixture checksum for every generated fixture.
- Treat Gemini outputs as model behavior, not as ground truth.

## Preprocessing Defaults

- Clinical: generate a small Synthea cohort and mark deterioration events with
  synthetic escalation labels.
- Cyber: extract labeled attack windows from CIC-IDS2017 flow CSVs and preserve
  timestamp ordering.
- Finance: sample transaction neighborhoods around suspicious labels.
- Research: sample FEVER claims with gold evidence IDs and labels.
- Infrastructure: sample trace windows with resource pressure and dependency
  contention.
- Legal: select CUAD clauses with known labels and evidence spans.
- Supply chain: sample item/store demand shocks and expected local/global
  response labels.
- Robotics: run seeded PettingZoo MPE/MPE2 episodes and store observations plus
  expected formation decisions.
- Emergency: sample CrisisMMD items with event type, informativeness, and
  response category labels.

## Sources

- Synthea: https://synthetichealth.github.io/synthea/
- CIC-IDS2017: https://www.unb.ca/cic/datasets/ids-2017.html
- IBM synthetic AML transactions: https://research.ibm.com/publications/realistic-synthetic-financial-transactions-for-anti-money-laundering-models
- FEVER: https://fever.ai/dataset/fever.html
- Alibaba Cluster Trace: https://github.com/alibaba/clusterdata
- CUAD: https://www.atticusprojectai.org/cuad/
- M5 forecasting paper: https://www.sciencedirect.com/science/article/pii/S0169207021001187
- PettingZoo MPE: https://pettingzoo.farama.org/main/environments/mpe/
- CrisisMMD: https://crisisnlp.qcri.org/crisismmd
