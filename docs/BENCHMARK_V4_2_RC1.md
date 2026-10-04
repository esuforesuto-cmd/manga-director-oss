# v4.2.0 RC1 Benchmark Audit

v4.2 benchmark smoke measures provider-free construction of immutable local
DTO projections. It does not measure model, provider, backend, network,
database, worker, or UI execution.

| Target | Smoke result | RC conclusion |
| --- | --- | --- |
| Execution Engine | DTO construction completes locally. | No execution-engine regression identified. |
| Checkpoint Management | DTO construction completes locally. | No repository mutation or regression identified. |
| Supervisor Runtime | DTO construction completes locally. | No monitoring/transport regression identified. |
| Background Tasks | DTO construction completes locally. | No scheduler or worker is enabled. |
| Planning / Pipeline / Recovery | DTO construction completes locally. | No automatic execution path is enabled. |
| Governance / Monitoring / Reliability | DTO construction completes locally. | No policy, telemetry, retry, or recovery action is enabled. |

The local smoke results are regression evidence for additive projections only;
hosted performance baselines remain a final-release gate.

## Latest local smoke

The v4.2 projection set completed 1,000 local constructions per target in
approximately 0.0067–0.0081 seconds on the RC validation environment. v4.1
paths were not modified, and v4.2 introduces no provider, backend, worker,
database, or network path that could regress their runtime behaviour.
