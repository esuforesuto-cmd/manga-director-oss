# v3.2 Benchmark Plan

All v3.2 benchmark candidates are provider-free, deterministic, one-Page
scoped, and non-executing. They measure DTO composition or bounded local
projections; they are not production SLOs.

| Scenario | Planned observation | Safety proof |
| --- | --- | --- |
| `asset_lookup` | Catalog/search projection composition. | Repository read-only; deterministic ordering; no remote lookup. |
| `workflow_profiles` | Profile/template validation composition. | StateMachine authority; no stage transition or application. |
| `production_analytics` | Bounded analytical report composition. | No collector, scheduler, deployment, or release action. |
| `creative_workspace` | Layout/session/dashboard DTO composition. | No write, Agent dispatch, quality pass, or approval. |
| `project_dashboard` | Existing Project/Workflow evidence aggregation. | One-Page scope and metadata redaction. |

Each executable benchmark needs a fixture, repeatability expectation,
observation window, and same-machine comparison baseline before implementation.
