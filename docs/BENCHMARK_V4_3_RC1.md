# v4.3.0 RC1 Benchmark Audit

v4.3 benchmark smoke measures provider-free construction of immutable local DTO
projections. It does not measure model, provider, backend, network, database,
worker, publishing, billing, or UI execution.

| Target | Smoke result | RC conclusion |
| --- | --- | --- |
| Production Pipeline / Asset Catalog | DTO construction completes locally. | No Repository mutation or execution path is enabled. |
| Project Analytics / Workspace | DTO construction completes locally. | No allocation, scheduling, or project mutation is enabled. |
| Publishing Workflow | DTO construction completes locally. | No export, upload, publication, distribution, or external call is enabled. |
| Governance / QA | DTO construction completes locally. | No enforcement, evaluation, remediation, or approval is enabled. |
| Monitoring / Reliability | DTO construction completes locally. | No telemetry, alert, retry, recovery, or remediation is enabled. |

## Latest local smoke

The v4.3 projection set completed 1,000 local constructions per target in
approximately 0.0047-0.0224 seconds on the RC validation environment. The
v4.2 public runtime paths were not modified. The new v4.3 paths are composite
DTO projections only, so the result does not claim provider, backend, worker,
database, network, or SLO performance.
