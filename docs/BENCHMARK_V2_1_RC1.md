# v2.1.0 RC1 Benchmark Smoke Comparison

## Method

The provider-free `benchmarks/smoke.py` harness was run from the same checkout
on 2026-07-26 using a clean venv with the retained v2.0.0rc1 wheel, then using
the RC1 source. Values are one warm local smoke sample in seconds; they are a
regression indicator, not a statistically significant throughput benchmark.

| Boundary | v2.0.0rc1 | v2.1.0rc1 | Result |
| --- | ---: | ---: | --- |
| Workflow | 0.002654 | 0.001407 | No regression observed |
| Repository | 0.000185 | 0.000182 | No regression observed |
| SQLite database | 0.007883 | 0.007483 | No regression observed |
| Prompt pipeline | 0.000500 | 0.000474 | No regression observed |
| Mock LLM | 0.000015 | 0.000013 | No regression observed |
| Mock Image | 0.000008 | 0.000007 | No regression observed |
| Mock Notification | 0.000027 | 0.000024 | No regression observed |
| Batch planning | 0.000022 | 0.000022 | No regression observed |

Automation is not benchmarked because no Automation runtime is included in the
source baseline. Network providers are intentionally excluded because they
would measure external service latency rather than Core regression behavior.

## Conclusion

No smoke-level performance regression was observed relative to the retained
v2.0.0rc1 wheel. Future release decisions should repeat this measurement with
multiple iterations and median/p95 reporting on a controlled runner.
