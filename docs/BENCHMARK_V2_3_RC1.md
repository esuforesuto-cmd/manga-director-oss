# v2.3.0 RC1 Benchmark Verification

## Method

The RC1 gate runs mock/provider-free benchmarks and existing retained-baseline
smoke tests. It compares the established v2.2 workload boundaries using the
project's conservative local regression thresholds and treats results as a
regression guard, not a cross-machine service-level objective.

## Result

The suite completed successfully on 2026-07-26. Workflow, repository,
database, batch, plugin, extension, notification, automation, provider/backend
runtime, diagnostics, and configuration paths completed without a threshold
failure. The repeatability smoke results recorded for v2.3 RC1 were:

| Boundary | Relative spread | Result |
| --- | ---: | --- |
| Workflow | 0.1398 | Passed (`<= 2.0`) |
| Repository | 0.1508 | Passed (`<= 2.0`) |
| Provider lifecycle | 0.6126 | Passed (`<= 2.0`) |
| Backend lifecycle | 1.0802 | Passed (`<= 2.0`) |
| Configuration governance | 0.0331 | Passed (`<= 2.0`) |

Provider and backend checks are local construction and metadata work only. No
external AI request, image generation, cloud service, or distributed workload
is represented by this result.
