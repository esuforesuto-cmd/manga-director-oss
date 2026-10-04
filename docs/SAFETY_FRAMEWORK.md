# Safety Framework Design

## Policy hierarchy

1. Core StateMachine and domain invariants
2. Human approval and quality-review boundaries
3. Execution policy and risk classification
4. Session, task, and checkpoint constraints
5. Advisory agent and supervisor recommendations

No lower policy may override a higher boundary.

## Risk classification

| Risk | Example | Required response |
| --- | --- | --- |
| Low | Read-only planning report | Human-visible evidence and normal review. |
| Medium | Resume proposal with intact checkpoint | Explicit human authorization and revalidation. |
| High | Missing storyboard, invalid state, integrity mismatch | Pause and escalate; no generation or transition. |
| Critical | Policy breach, approval attempt, unsafe multi-page scope | Emergency stop and human investigation. |

## Emergency stop and audit trail

Emergency stop is a proposed human-controlled command that prevents future
session dispatch. It must be fail-closed, explainable, and auditable. Audit
trail design must record policy identity, decision rationale, evidence hashes,
actor, timestamp, and redaction classification, but v4.2 planning does not
create a persistent audit store.
