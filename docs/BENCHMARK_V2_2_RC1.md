# v2.2.0 RC1 Benchmark Comparison

## Method

The RC1 quality gate runs provider-free local benchmark scripts and compares
the five established workload boundaries against the retained v2.1 threshold
artifact in `benchmarks/baselines/v2_1.json`. That artifact uses an 8×
multiplier and a 0.1 second floor to identify material regressions across
machines; it is not a claim of absolute performance or a controlled p95 study.

The RC1 suite also runs plugin, extension, event dispatch, configuration,
diagnostics, and repeatability smoke paths. Network providers and the absent
Automation runtime are intentionally excluded.

## Result

The following one-run local values were collected on 2026-07-26. Established
workload values passed the retained v2.1 regression thresholds; runtime and
repeatability scenarios completed successfully.

| Boundary | RC1 seconds | Result |
| --- | ---: | --- |
| Large Project aggregate | 0.000765 | Passed retained v2.1 threshold |
| Repository index | 0.000530 | Passed retained v2.1 threshold |
| SQLite query | 0.002543 | Passed retained v2.1 threshold |
| Batch resume | 0.247025 | Passed retained v2.1 threshold |
| Workflow scale | 0.022852 | Passed retained v2.1 threshold |
| Plugin loading | 0.048328 | Runtime smoke passed |
| Extension loading | 0.000104 | Runtime smoke passed |
| Event dispatch | 0.000609 | Runtime smoke passed |
| Configuration load | 0.062138 | Runtime smoke passed |
| Diagnostics composition | 0.001536 | Runtime smoke passed |

Five provider-free repeatability scenarios also passed their stability tests.
No benchmark threshold may be relaxed in the RC process. A failure requires a
corrective change or a documented release block.

## Interpretation

- Compare only provider-free local paths on the same environment.
- Treat the retained v2.1 thresholds as a regression guard, not a service
  level objective.
- Use repeated controlled measurements and median/p95 values before making
  performance claims for a deployment.
