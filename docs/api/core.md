# `bca2p.core`

`bca2p.core` contains the public protocol objects that every later phase depends on.

## Main Objects

- `SignalEnvelope`
  - canonical typed signal carrier
- `ReceptorSpec`
  - receiver contract and payload binding
- `ComplexSpec`
  - temporary coalition definition
- `QuorumRule`
  - threshold-triggered group action definition
- `HomeostasisPolicy`
  - stabilization and throttling policy
- `TopologyPolicy`
  - adaptive topology policy
- `CausalFeedback`
  - downstream structured feedback for learning
- `AgentProfile`
  - public agent identity and receptor catalog
- `ArtifactRef`
  - structured attachment or artifact reference

## Serialization

All public core objects inherit from `ProtocolModel`.

`ProtocolModel` provides:

- `to_dict()`
- `from_dict()`
- schema metadata stamping through `_schema`

Example:

```python
from bca2p.core import SignalEnvelope, SignalMode

signal = SignalEnvelope(
    signal_id="sig-1",
    mode=SignalMode.PARACRINE,
    sender="planner",
    recipient_scope="research.team",
    payload={"query": "map patents"},
)

serialized = signal.to_dict()
restored = SignalEnvelope.from_dict(serialized)
```

## Validation Model

- All models use Pydantic v2 validation.
- Unknown fields are rejected.
- Numeric safety bounds are enforced for confidence, decay, thresholds, and amplification-related controls.
- Schema version mismatches raise `SchemaVersionError`.
