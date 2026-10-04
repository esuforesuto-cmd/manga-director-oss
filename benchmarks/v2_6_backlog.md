# v2.6 Benchmark Planning Backlog

The following are planning specifications, not runnable performance claims.

| Scenario | Purpose | Required before implementation |
| --- | --- | --- |
| `workflow_planning` | Measure one-page advisory planning DTO construction. | Legal-step fixture, baseline, no state mutation assertion. |
| `provider_selection` | Measure metadata-only capability matching. | Mock registry, cache policy, no provider invocation. |
| `provider_fallback` | Measure non-executing fallback-plan construction. | Deterministic estimates, no transport retry. |
| `workflow_diagnostics` | Measure bounded diagnostic/report construction. | Redaction fixture and retention policy. |
| `operations_planning` | Measure maintenance/capacity plan DTO construction. | Repository-port fixture, no cleanup or scheduling. |
