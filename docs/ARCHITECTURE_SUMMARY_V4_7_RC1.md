# v4.7 RC1 Architecture Summary

## Review outcome

The v4.7 Creative Decision Platform is an additive Application/Production
projection layer. `v4_7_decision_foundation`, `v4_7_decision_intelligence`,
and `v4_7_decision_governance` consume caller-supplied DTO evidence only. They
do not depend on API, CLI, MCP, Repository, presentation, or workflow-execution
layers.

## Boundary review

| Area | RC1 boundary |
| --- | --- |
| Decision Engine | Context, evidence, alternatives, risk, and uncertainty remain human-owned; no collection, persistence, selection, enforcement, agent dispatch, or workflow action occurs. |
| Recommendation Framework | Advisory rationale, prerequisite, impact, and confidence evidence remains human-reviewed; no ranking, selection, acceptance, dispatch, scheduling, or mutation occurs. |
| Review Intelligence | Review evidence and audit trace requirements remain diagnostic; no review completion, finding mutation, approval, or quality-gate bypass occurs. |
| Approval Platform | Approval readiness retains StateMachine, storyboard, completed-quality-review, and human-approval prerequisites; no authentication, access grant, submission, grant, override, or transition occurs. |
| Executive Dashboard | Dashboard composition is transport-neutral and presentation-independent; no collection, persistence, publication, telemetry, monitoring, alert, policy enforcement, routing, or organizational action occurs. |
| Governance and reliability | Policy, compliance, audit, and reliability reports are advisory DTOs; no enforcement, attestation, monitoring, retry, recovery, persistence, or operational action occurs. |
| Workflow safety | The existing StateMachine remains authoritative. No v4.7 module changes the one-page, storyboard, quality-review, or human-approval safeguards. |

## Delivery surfaces

Existing CLI, FastAPI, REST API, MCP, and Web UI remain adapters to their
pre-existing application services. They are not imported by v4.7 modules. This
keeps RC1 DTOs transport-neutral and avoids a Core Architecture change.

See [the RC release notes](../RELEASE_V4_7_RC1.md) and [compatibility
verification](COMPATIBILITY_V4_7_RC1.md).
