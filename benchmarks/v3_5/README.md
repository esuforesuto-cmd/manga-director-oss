# v3.5 Benchmark Candidates

This directory records design-only benchmark candidates for the v3.5 planning
cycle. Every candidate is provider-free, deterministic, one-Page scoped, and
non-executing; it does not write through a Repository, generate content,
schedule work, deploy, tag, sign, publish, collect remotely, or execute a
workflow.

| Candidate | Scope | Required guard |
| --- | --- | --- |
| `knowledge_graph` | Relationship/context/traceability projection. | No graph persistence, remote lookup, or Repository write. |
| `creative_metrics` | Story/character/page-quality projection. | No creative generation, change, approval, or review bypass. |
| `production_metrics` | Efficiency/pipeline/capacity/risk projection. | No scheduling, allocation, workflow change, remediation, or deploy. |
| `platform_health` | Local cross-platform health projection. | No monitoring action, collection, retention, or alert. |
| `analytics_dashboard` | Executive/trend/history/regression projection. | No release authorization or external action. |

See [the benchmark plan](../../docs/V3_5_BENCHMARK_PLAN.md).

## Iteration 2 scenarios

`knowledge_graph_v35`, `creative_intelligence`, `production_intelligence_v35`,
and `platform_dashboard` measure provider-free DTO reporting only. They do not
persist graph or analytics data, generate content, approve a Page, schedule,
deploy, collect remotely, or trigger an external action.

## Iteration 3 scenarios

`governance_dashboard_v35`, `policy_validation_v35`,
`compliance_report_v35`, and `audit_generation_v35` measure deterministic,
DTO-only governance evidence. They do not store/enforce policy, persist/export
audits, modify a workflow, approve a Page, monitor, deploy, or call an
external service.
