# v2.4 Benchmark Backlog

These are specifications only. A benchmark becomes executable after an
accepted Issue provides deterministic mock/local fixtures, environment metadata,
baseline, budget, and rollback criterion.

| Scenario | Candidate Issue | Measurement boundary |
| --- | --- | --- |
| `provider_selection` | ECO-LLM-01 | Factory discovery/alias selection; no request |
| `provider_failover` | ECO-LLM-02 | Declarative fallback policy/health; no live provider |
| `workflow_production` | PROD-01 | page recovery/save/resume with mock Agents |
| `repository_large_project` | PROD-02 | indexes/history/integrity on deterministic aggregate |
| `diagnostics_large_project` | MON-04 | safe summaries/exports under bounded fixture size |

Do not benchmark external AI latency, Cloud services, or actual image generation
in CI. The existing smoke and repeatability suite remains the v2.3 baseline.
