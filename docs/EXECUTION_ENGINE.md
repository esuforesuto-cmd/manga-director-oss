# Execution Engine Design

## Proposed session state model

```text
Defined → AwaitingHumanStart → Planned → Paused ↔ Resumable
                              ↓
                     AwaitingHumanReview → Closed
                              ↓
                         EmergencyStopped
```

These are proposed execution-session states only. They do not replace PageState
or create a new workflow state machine. A future implementation must map each
action to one legal existing Page transition and must never issue more than one
Page request.

## Checkpoint contract

Checkpoint candidates contain immutable goal/session/task identifiers, the
current Page reference, workflow state, artifact references, policy version,
and a human-readable stop/resume rationale. Future persistence requires
retention, integrity, access-control, redaction, and repository compatibility
review.

## Pause and resume

Only a human-authorized policy decision may initiate or resume an execution
session. Resume must revalidate configuration, policy, StateMachine legality,
persisted storyboard evidence, and quality-review/approval boundaries.
