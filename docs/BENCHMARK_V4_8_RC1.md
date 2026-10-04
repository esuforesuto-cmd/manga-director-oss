# v4.8 RC1 Benchmark Verification

## Coverage

The RC benchmark set is provider-free and measures construction of bounded
v4.7 and v4.8 DTO/report projections.

| Benchmark | Reviewed operation | Safety boundary |
| --- | --- | --- |
| `decision_foundation_v4_7.py` | v4.7 Decision Foundation construction | No collection, persistence, selection, approval, or workflow execution. |
| `decision_intelligence_v4_7.py` | v4.7 Decision Intelligence construction | No autonomous decision, recommendation acceptance, approval, or telemetry. |
| `decision_governance_v4_7.py` | v4.7 Decision Governance construction | No policy enforcement, monitoring, alerting, retry, or recovery. |
| `creative_operating_system_v4_8.py` | v4.8 integrated operations report construction | No service action, telemetry, enforcement, persistence, or workflow execution. |

## Result

The local RC verification environment completed 1,000 constructions for each
projection:

| Projection | Local RC1 result (1,000 constructions) |
| --- | ---: |
| v4.7 Foundation | 0.027660s |
| v4.7 Intelligence | 0.065441s |
| v4.7 Governance | 0.185304s |
| v4.8 Creative Operating System | 0.158456s |

Results are local throughput evidence only, not a cross-machine performance
promise. Existing v4.7 runtime paths are unchanged, and the new v4.8
provider-free composition is bounded; no material performance regression in an
existing runtime path was identified.

See [the release checklist](RELEASE_CHECKLIST_V4_8_RC1.md).
