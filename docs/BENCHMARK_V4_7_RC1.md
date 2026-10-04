# v4.7 RC1 Benchmark Verification

## Coverage

The RC benchmark set is provider-free and measures construction of bounded
v4.7 DTO/report projections.

| Benchmark | Reviewed operation | Safety boundary |
| --- | --- | --- |
| `decision_foundation_v4_7.py` | Executive Decision Foundation construction | No collection, persistence, selection, approval, or workflow execution. |
| `decision_intelligence_v4_7.py` | Executive Decision Intelligence Dashboard construction | No autonomous decision, recommendation acceptance, approval, or telemetry. |
| `decision_governance_v4_7.py` | Executive Decision Governance Dashboard construction | No policy enforcement, monitoring, alerting, retry, or recovery. |

## Result

The local RC verification environment completed 1,000 constructions for each
projection:

| Projection | v4.7 RC1 review projection (1,000 constructions) |
| --- | ---: |
| Foundation | 0.028919s |
| Intelligence | 0.063670s |
| Governance | 0.192000s |

Results are local throughput evidence only, not a cross-machine performance
promise. v4.7 adds no workflow, repository, network, provider, model-update,
agent-runtime, or operational-execution path; no material v4.6 runtime-path
performance regression was identified.

See [the release checklist](RELEASE_CHECKLIST_V4_7_RC1.md).
