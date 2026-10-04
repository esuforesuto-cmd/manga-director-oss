# v3.4 Benchmark Candidates

This directory records design-only benchmark candidates for the v3.4 planning
cycle. Every candidate is provider-free, deterministic, one-Page scoped, and
non-executing; no workflow execution, Repository write, person assessment,
deployment, tagging, signing, publication, or remote lookup is measured.

| Candidate | Scope | Required guard |
| --- | --- | --- |
| `knowledge_platform` | Catalog/relationship/search projection. | Repository read-only; no remote lookup or write. |
| `operations_dashboard` | Operations snapshot projection. | No monitoring action, remediation, or deployment. |
| `organization_health` | Redacted organization evidence aggregation. | No scoring, assignment, or membership action. |
| `release_health` | Release evidence aggregation. | No tagging, signing, publishing, deploying, or approval. |
| `deployment_analytics` | Supplied deployment evidence comparison. | No deployment operation or release action. |

See [the benchmark plan](../../docs/V3_4_BENCHMARK_PLAN.md).
