# v3.2 Benchmark Candidates

This directory records design-only benchmark candidates for the v3.2 planning
cycle. Iteration 1 adds local executable DTO projection benchmarks in the
parent directory; they measure no workflow execution, repository write, remote
lookup, or approval operation.

| Candidate | Scope | Required guard |
| --- | --- | --- |
| `asset_lookup` | Bounded catalog/search projection. | Repository read-only; no remote lookup. |
| `workflow_profiles` | Template/profile validation composition. | StateMachine authority; no profile application. |
| `production_analytics` | Bounded analytical report composition. | No collector or operational action. |
| `creative_workspace` | Workspace/session layout composition. | No write, dispatch, quality pass, or approval. |
| `project_dashboard` | Existing Project/Workflow aggregation. | Exactly one Page evidence and redaction. |

Iteration 1 implementations: `../creative_studio.py`,
`../asset_intelligence.py`, `../workflow_profiles.py`,
`../production_analytics.py`, and `../workspace_dashboard.py`.

See [the benchmark plan](../../docs/V3_2_BENCHMARK_PLAN.md).
