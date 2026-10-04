# v4.6 RC1 Benchmark Verification

## Coverage

The RC benchmark set is provider-free and measures construction of bounded
v4.6 DTO/report projections. It covers:

| Benchmark | Reviewed operation | Safety boundary |
| --- | --- | --- |
| `intelligence_foundation_v4_6.py` | Intelligence Hub foundation construction | No context collection/persistence, memory operation, or workflow execution. |
| `intelligence_analysis_v4_6.py` | Intelligence Dashboard construction | No model update, autonomous decision, persistence, or telemetry. |
| `intelligence_governance_v4_6.py` | Intelligence Operations Validation construction | No policy enforcement, monitoring, alerting, retry, or recovery. |

## Result

The RC benchmark commands completed successfully in the release verification
environment:

| Projection | v4.6 RC1 review projection (1,000 constructions) |
| --- | ---: |
| Foundation | 0.029172s |
| Analysis | 0.067869s |
| Governance | 0.188881s |

Results are local throughput evidence only, not a cross-machine performance
promise. The projections are in-memory DTO construction and do not add a
workflow, repository, network, provider, model-update, agent-runtime, or
operational-execution path. v4.6 does not alter an existing v4.5 runtime path;
no material compatibility-surface performance regression was identified.

See [the release checklist](RELEASE_CHECKLIST_V4_6_RC1.md).
