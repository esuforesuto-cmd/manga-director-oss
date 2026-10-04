# v4.6 Architecture Report: Creative Intelligence OS

## Decision

v4.6 is a design-only cycle. It proposes transport-neutral, additive planning
surfaces above stable v4.5.0. Core domain authority, StateMachine,
WorkflowEngine, existing Repository interfaces, Agent Platform, Plugin
contracts, and Extension SDK contracts remain unchanged.

## Proposed intelligence model

```text
Human owner / editor / reviewer / operations lead
                    |
Creative Intelligence OS planning surfaces
  |- Unified Creative Context
  |- Cross-Agent Memory references
  |- Creative Reasoning reports
  |- Adaptive Workflow proposals
  `- Intelligence Hub review packet
                    |
v4.5 Ecosystem + existing Agent, Knowledge, Workflow, Creative Intelligence,
and Enterprise Platform evidence
                    |
StateMachine, WorkflowEngine, Project Repository, Agent / Plugin / Extension SDK
```

Every proposed surface consumes caller-supplied, local, redacted evidence and
returns immutable descriptors, findings, plans, recommendations, or reports. It
has no authority to mutate state, persist memory, access another agent's
context, dispatch an agent, execute a workflow, invoke a service, synchronize
data, publish a result, enforce a policy, or call an external service.

## Responsibility boundaries

| Area | Future additive responsibility | Must not own |
| --- | --- | --- |
| Unified Creative Context | Context schema, provenance, redaction, freshness, scope, and review-ready composition. | Project mutation, implicit context collection, persistence, access enforcement, or tenant routing. |
| Cross-Agent Memory | Attributable memory-reference, consent, conflict, coverage, and recall-readiness evidence. | Memory writes, synchronization, merge, transfer, automatic retrieval, or agent communication. |
| Creative Reasoning | Explainable goals, alternatives, evidence links, risk, confidence, and recommendation reports. | Autonomous choice, prompt execution, agent delegation, approval, or learning. |
| Adaptive Workflow | Human-reviewable adaptation candidate, dependency, safety, rollback, and impact evidence. | State transition, stage skipping, workflow edit/execution, scheduling, retry, or recovery. |
| Intelligence Hub | Cross-domain summary, trace, KPI, and review-packet composition. | Dashboard persistence/publication, presentation ownership, telemetry, alerting, or operational action. |

## Implementation admission criteria

Every future implementation issue must demonstrate additive API compatibility,
explicit context provenance and consent, redaction review, exactly-one-Page
scope where workflow evidence is involved, StateMachine delegation, persisted
storyboard before image generation, completed quality review before approval,
no implicit write or dispatch, and a human-approved rollback plan.
