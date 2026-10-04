# v4.7 Architecture Report: Creative Decision Platform

## Decision

v4.7 is a design-only cycle over stable v4.6.0. It proposes transport-neutral,
additive decision-support DTOs at the Application layer. Core domain authority,
StateMachine, WorkflowEngine, existing Repository interfaces, Agent Platform,
Review, Governance, Analytics, and Enterprise Platform contracts remain
unchanged.

## Proposed decision model

```text
Human owner / editor / reviewer / approver / executive sponsor
                            |
Creative Decision Platform planning surfaces
  |- Decision Engine
  |- Review Intelligence
  |- Recommendation Framework
  |- Approval Platform
  `- Executive Dashboard
                            |
v4.6 Context, Memory, Reasoning, Workflow, Governance, Observability,
Reliability + existing Review, Analytics, and Enterprise evidence
                            |
StateMachine, WorkflowEngine, Project Repository, Agent / Plugin / Extension SDK
```

Every surface consumes explicitly supplied evidence and produces immutable
descriptors, findings, comparisons, recommendations, approval requests, or
summaries. It cannot persist evidence, enforce policy, accept or grant approval,
dispatch an agent, transition workflow state, execute work, collect telemetry,
or call an external service.

## Responsibility boundaries

| Area | Future additive responsibility | Must not own |
| --- | --- | --- |
| Decision Engine | Decision context, alternatives, trade-offs, evidence links, uncertainty, risk, owner, and trace DTOs. | Decision execution, acceptance, persistence, policy enforcement, or workflow transition. |
| Review Intelligence | Supplied review finding aggregation, coverage, consistency, confidence, and reviewer-ready summary DTOs. | Automatic review, content approval, finding mutation, or quality-gate bypass. |
| Recommendation Framework | Explainable option, impact, confidence, prerequisite, and human-review recommendation DTOs. | Option selection, action dispatch, policy interpretation, or automatic remediation. |
| Approval Platform | Manual approval request, role expectation, escalation, override rationale, and history-reference DTOs. | Authentication, authorization, access grant, actual approval, enforcement, or persistence. |
| Executive Dashboard | Redacted cross-domain decision-health, risk, review, approval-readiness, and trend summaries. | Presentation ownership, data collection, publication, telemetry, monitoring, or organizational action. |

## Implementation admission criteria

Every future implementation issue must demonstrate additive API compatibility,
caller-supplied provenance and redaction, explicit human owner/reviewer/approver,
exactly-one-Page scope where workflow evidence is involved, StateMachine
delegation, persisted storyboard before image generation, completed quality
review before approval, no implicit write or dispatch, and a human-approved
rollback plan.
