# v2.6.0 RC1 Benchmark Verification

Provider-free benchmark smoke exercises workflow, repository, planning,
analysis, provider/backend runtime, automation, diagnostics, reporting, and
health. It covers the v2.6 advisory paths without a real provider, image
backend, network request, or workflow execution.

The v2.5 stable baseline did not persist cross-host absolute performance data
for the v2.6 advisory paths. Therefore this RC uses deterministic local smoke
and repeatability evidence rather than treating a different host as a numeric
baseline. No local regression was identified in retained workflow or repository
smoke paths. Results are not a production SLO or cross-machine comparison.

Live providers, cloud monitoring, distributed execution, and autonomous
workflow execution are intentionally excluded from this RC benchmark scope.

## Review-host smoke timings

| Path | Elapsed |
| --- | ---: |
| Workflow | 0.001574 s |
| Repository | 0.000189 s |
| Database | 0.006579 s |
| Workflow planning (500 iterations) | 0.008268 s |
| Provider selection (500 iterations) | 0.021946 s |
| Workflow analysis (500 iterations) | 0.067127 s |
| Provider comparison (500 iterations) | 0.033881 s |
| Workflow validation (500 iterations) | 0.152862 s |
| Provider governance (500 iterations) | 0.019590 s |
| Enterprise readiness (500 iterations) | 0.104343 s |
| Workflow health (500 iterations) | 0.234193 s |
