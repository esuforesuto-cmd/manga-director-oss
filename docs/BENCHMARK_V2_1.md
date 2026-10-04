# v2.1.0 Benchmark Smoke Comparison

## Method

The provider-free `benchmarks/smoke.py` harness ran in the same checkout on
2026-07-26, first with the retained `2.0.0rc1` wheel and then with the v2.1.0
source. Values are one warm local sample in seconds. They detect obvious
regressions; they are not a statistically significant benchmark.

| Boundary | v2.0.0rc1 | v2.1.0 | Result |
| --- | ---: | ---: | --- |
| Workflow | 0.002654 | 0.001560 | No regression observed |
| Repository | 0.000185 | 0.000187 | No regression observed |
| SQLite database | 0.007883 | 0.007704 | No regression observed |
| Prompt pipeline | 0.000500 | 0.000538 | No regression observed |
| Mock LLM | 0.000015 | 0.000014 | No regression observed |
| Mock Image | 0.000008 | 0.000007 | No regression observed |
| Mock Notification | 0.000027 | 0.000028 | No regression observed |
| Batch planning | 0.000022 | 0.000023 | No regression observed |

Automation is excluded because the source baseline has no Automation runtime.
Network providers are excluded because external latency is not a Core
regression measure.

## Conclusion

No smoke-level performance regression was observed. Future releases should use
multiple controlled-run iterations and median/p95 reporting.
