# v5.1.0 RC1 Benchmark Verification

Local 1,000-iteration measurements on 2026-08-03:

| Projection | Elapsed | Result |
| --- | ---: | --- |
| v5 Unified Platform maturity report | 0.056326 s | No regression against the prior v5 local reference (0.059445 s). |
| v5.1 Composition Platform maturity report | 0.044031 s | Local metadata-only composition completes without runtime activation. |

Measurements use [unified_platform_v5.py](../benchmarks/unified_platform_v5.py)
and [composition_platform_v5_1.py](../benchmarks/composition_platform_v5_1.py).
They are local regression indicators, not hosted performance claims.
