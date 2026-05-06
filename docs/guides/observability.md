# Observability Guide

The observability layer records structured runtime events and topology snapshots so users can inspect communication behavior over time.

## Event Types

- signal emitted
- signal delivered
- signal dropped
- complex formed
- quorum triggered
- homeostasis intervention

## Example

```python
from bca2p.observability import TraceRecorder

recorder = TraceRecorder(trace_id="trace-1")
bundle_json = recorder.to_json()
```
