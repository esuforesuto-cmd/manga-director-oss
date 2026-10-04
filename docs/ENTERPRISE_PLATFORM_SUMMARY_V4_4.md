# v4.4 Enterprise Platform Summary

v4.4 ships an additive Enterprise Creative Platform as immutable DTO and
Application-service projections. It has no direct dependency on CLI, FastAPI,
MCP, presentation, repository, or workflow execution layers.

| Area | Stable boundary |
| --- | --- |
| Workspace / Collaboration | One-Page-scoped human-review evidence; no membership, assignment, approval, or workflow action. |
| Portfolio | Caller-supplied observation; no persistence, allocation, scheduling, or Project mutation. |
| Extension Registry / Marketplace | Local evidence only; no discovery, installation, loading, execution, publishing, payment, or billing. |
| Governance / Reliability | Advisory reports only; no enforcement, monitoring, alerting, retry, recovery, or external operation. |
| Workflow | Existing StateMachine remains authoritative and unchanged. |

See [Compatibility Verification](COMPATIBILITY_V4_4.md) and
[Workflow Regression](WORKFLOW_REGRESSION_V4_4.md).
