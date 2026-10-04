# Adaptive Workflow

Adaptive Workflow is the v4.6 planning model for presenting a safe adaptation
candidate for human review. It is not a workflow editor, scheduler, recovery
engine, or automatic execution system.

## Adaptation proposal

| Element | Planning responsibility | Boundary |
| --- | --- | --- |
| Trigger evidence | Describe a supplied bottleneck, risk, inconsistency, or quality signal. | No monitoring, polling, incident detection, or alerting. |
| Candidate change | Explain an optional sequencing, dependency, review, or evidence-collection proposal. | No workflow mutation, stage change, dispatch, or execution. |
| Safety analysis | Show one-page scope, StateMachine, storyboard, quality-review, approval, governance, and rollback prerequisites. | No automatic validation, enforcement, or approval. |
| Impact analysis | Compare expected benefits, risks, dependencies, and confidence. | No forecast commitment, capacity allocation, or operational action. |
| Human decision record | Reserve acceptance, rejection, or deferral for an existing human-governed surface. | No decision persistence or automatic action. |

Any later implementation must delegate legal transitions to the StateMachine and
preserve exactly one page per workflow execution. It must never skip a stage,
generate an image without a persisted storyboard, approve without a completed
quality review, or accept a multi-page generation request.

See [Unified Creative Context](UNIFIED_CREATIVE_CONTEXT.md).
