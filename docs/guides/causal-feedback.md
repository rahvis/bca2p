# Causal Feedback Guide

`bca2p.learning` turns structured outcomes into usable communication insights.

## What It Stores

- signal edges
- decision nodes
- outcome nodes
- contributor scores

## What It Answers

- What if a signal had stayed local?
- What if a complex member had been absent?
- What if amplification had been lower?

## Example

```python
from bca2p.core import CausalFeedback, ContributionFactor, FeedbackType, SignalEnvelope, SignalMode
from bca2p.learning import CausalGraphStore

store = CausalGraphStore()

signal = SignalEnvelope(
    signal_id="sig-1",
    mode=SignalMode.PARACRINE,
    sender="planner",
    recipient_scope="research.team",
    receptor="research.query",
    payload={"query": "map patents"},
)

store.record_signal(signal, step=1)
store.ingest_feedback(
    CausalFeedback(
        target_signal_id="sig-1",
        feedback_type=FeedbackType.OUTCOME,
        outcome="success",
        confidence=0.9,
        contributors=[
            ContributionFactor(source_id="planner", contribution=0.8),
        ],
    ),
    step=2,
)

summary = store.summarize_contributions("sig-1")
counterfactual = store.what_if_signal_stayed_local("sig-1")
```
