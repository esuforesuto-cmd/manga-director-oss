# v3.1 Benchmark Plan

All v3.1 benchmark candidates are provider-free, deterministic, one-Page
scoped, and non-executing. They measure DTO composition or bounded local
projection only; they are not production SLOs.

| Scenario | What it will measure | Required safety proof |
| --- | --- | --- |
| `planning_quality` | Template/strategy comparison report composition. | No Agent, Provider, or state transition. |
| `knowledge_evolution` | Version/diff/snapshot/timeline projection composition. | Repository read-only and metadata-value redaction. |
| `workflow_metrics` | Bounded one-Page metric/timeline aggregation. | No scheduler, multi-page execution, or mutation. |
| `operations_dashboard` | Health/quality/release/project dashboard report composition. | No external telemetry, configuration, or release action. |
| `creative_collaboration` | Workspace/hand-off/review-plan report composition. | No artifact mutation, quality pass, or approval. |

Each later executable benchmark needs a fixture, repeatability expectation,
documented observation window, and a comparison baseline captured on the same
machine class.
