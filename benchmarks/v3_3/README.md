# v3.3 Benchmark Candidates

This directory records design-only benchmark candidates for the v3.3 planning
cycle. Every candidate is provider-free, deterministic, one-Page scoped, and
non-executing; no workflow execution, Repository write, archive/delete,
approval, publishing, scheduling, or remote lookup is measured.

| Candidate | Scope | Required guard |
| --- | --- | --- |
| `production_pipeline` | Template/stage/validation projection. | StateMachine authority; no transition, approval, or publishing. |
| `quality_metrics` | Quality/review/consistency aggregation. | No quality pass, score authority, or approval. |
| `asset_lifecycle` | Lifecycle/history/dependency/audit projection. | Repository read-only; no archive/delete. |
| `project_health` | Project/schedule/milestone/risk aggregation. | No Project mutation or scheduling. |
| `delivery_forecast` | Supplied forecast-assumption report. | No delivery commitment or operational action. |

See [the benchmark plan](../../docs/V3_3_BENCHMARK_PLAN.md).
