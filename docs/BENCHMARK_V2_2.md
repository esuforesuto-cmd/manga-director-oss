# v2.2.0 Benchmark Verification

## Method

The stable release reruns the provider-free local workload and repeatability
scenarios from RC1. The five established workload paths use the retained v2.1
threshold artifact in `benchmarks/baselines/v2_1.json`; its conservative 8×
multiplier and 0.1 second floor detect material regressions rather than define
cross-machine service-level objectives.

## Result

| Boundary | Stable seconds | Result |
| --- | ---: | --- |
| Large Project aggregate | 0.000772 | Passed retained v2.1 threshold |
| Repository index | 0.000457 | Passed retained v2.1 threshold |
| SQLite query | 0.002401 | Passed retained v2.1 threshold |
| Batch resume | 0.239042 | Passed retained v2.1 threshold |
| Workflow scale | 0.022892 | Passed retained v2.1 threshold |
| Plugin loading | 0.052096 | Runtime smoke passed |
| Extension loading | 0.000104 | Runtime smoke passed |
| Event dispatch | 0.000563 | Runtime smoke passed |
| Configuration load | 0.058258 | Runtime smoke passed |
| Diagnostics composition | 0.001477 | Runtime smoke passed |

Five provider-free repeatability scenarios passed their stability checks. No
network provider or Automation runtime is included: neither belongs to the
shipped Core performance boundary.

## Interpretation

Use controlled multi-run median/p95 measurements before making deployment
capacity claims. The release gate verifies regressions, not universal
throughput.
