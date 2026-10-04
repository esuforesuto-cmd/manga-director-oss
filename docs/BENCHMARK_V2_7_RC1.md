# v2.7.0 RC1 Benchmark Verification

Provider-free benchmark smoke exercises Workflow, Repository, Knowledge search,
Workflow planning, Workflow analysis, Provider Runtime, diagnostics, reporting,
and health. The v2.7 paths use local mock metadata and frozen DTO composition;
they make no network request, call no provider, or execute a workflow.

The v2.6 stable baseline did not persist cross-host absolute performance data
for the v2.7 advisory paths. This RC therefore uses deterministic local smoke
and repeatability evidence rather than treating a different host as a numeric
baseline. No local regression was identified in retained workflow or repository
smoke paths. Results are not a production SLO or cross-machine comparison.

## Review-host smoke timings

| Path | Elapsed |
| --- | ---: |
| Workflow | 0.001544 s |
| Repository | 0.000192 s |
| Database | 0.006662 s |
| Workflow planning (500 iterations) | 0.008658 s |
| Workflow analysis (500 iterations) | 0.069389 s |
| Director reliability (500 iterations) | 0.076056 s |
| AI workflow diagnostics (500 iterations) | 0.352651 s |

Live providers, cloud monitoring, distributed execution, and autonomous
workflow execution remain intentionally excluded from this RC benchmark scope.
