# v2.5 Benchmark Backlog

These are planning specifications only. A scenario becomes runnable after an
accepted Issue provides deterministic mock/local fixtures, environment metadata,
baseline, budget, and rollback criterion.

| Scenario | Candidate Issue | Measurement boundary |
| --- | --- | --- |
| `provider_selection` | V25-ECO-01 | Factory discovery, alias, capability, and priority diagnostics; no request. |
| `backend_selection` | V25-ECO-01 | Backend discovery, preset, and workflow-metadata selection; no generation. |
| `production_workflow` | V25-PROD-01 | One-page mock recovery/save/reload/resume and explicit approval evidence. |
| `large_repository` | V25-REP-01 | Indexed metadata, bounded history, integrity, and recovery across a deterministic aggregate. |
| `diagnostics_pipeline` | V25-DIAG-01 | DTO-only JSON/Markdown diagnostics composition and redaction. |
| `quality_pipeline` | V25-QA-01 | Provider-free quality gate orchestration and documented evidence collection. |

Do not benchmark external AI latency, Cloud services, real credentials, actual
image generation, or hardware-dependent throughput in CI.
