# v4.4 RC1 Benchmark Verification

## Method

Benchmarks construct provider-free, immutable Enterprise Platform projections
1,000 times. They measure DTO/report construction only; they do not invoke a
provider, repository write, network call, workflow execution, marketplace, or
extension runtime.

## Coverage

- `benchmarks/enterprise_foundation_v4_4.py`
- `benchmarks/enterprise_intelligence_v4_4.py`
- `benchmarks/enterprise_governance_v4_4.py`

## RC1 result

| Projection | 1,000 constructions |
| --- | ---: |
| Enterprise Foundation | 0.003751 s |
| Enterprise Intelligence | 0.029565 s |
| Enterprise Governance | 0.085989 s |

The provider-free run completed without a regression requiring a source
correction relative to the v4.3 projection baseline.

See the [RC readiness report](V4_4_RC1_READINESS_REPORT.md).
