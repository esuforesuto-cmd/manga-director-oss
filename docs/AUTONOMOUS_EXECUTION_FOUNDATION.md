# Autonomous Execution Foundation

v4.2 adds an Application-layer DTO foundation for a future supervised
execution system. It is not an execution engine: sessions are defined but not
started, goals are human-owned, and execution remains disabled.

| DTO | Purpose | Disabled boundary |
| --- | --- | --- |
| `GoalDTO` | Exactly-one-Page objective and success criteria. | Autonomous goal selection, approval, and multi-page scope. |
| `ExecutionContextDTO` | Current workflow evidence and prerequisites. | Workflow mutation, persistence, and StateMachine replacement. |
| `ExecutionSessionDTO` | Human-start-required session declaration. | Start, dispatch, model invocation, and durable session state. |
| `ExecutionStateDTO` | Local `defined` state projection. | State transition and workflow change. |
| `ExecutionSummary` | Prepared-session counts. | Autonomous decision or action. |

Every future action must be exactly one Page scoped and use the existing
StateMachine. A persisted storyboard remains mandatory before image generation,
and a completed quality review remains mandatory before approval.

## AI Execution Runtime boundary

`V42AutonomousFoundationService.execution()` is a public, read-only runtime
preview. It returns an `AutonomousExecutionReport` for one existing workflow
page, including whether storyboard evidence is present; it never starts a
session, invokes a model, changes the `WorkflowContext`, or advances the
StateMachine. Missing evidence is reported for human review, not repaired or
executed automatically.
