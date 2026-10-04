# Review Pipeline

## Planned pipeline

The pipeline models evidence requirements, not reviewer execution. Each stage
records a declared outcome, responsible human role, and evidence reference.

| Gate | Required evidence | Output | Authority boundary |
| --- | --- | --- | --- |
| Scope check | One Page and current workflow state | Scope finding | Cannot start or transition workflow. |
| Storyboard check | Persisted storyboard reference | Storyboard finding | Cannot generate an image. |
| Creative review | Completed quality-review evidence | Review finding | Cannot approve a Page. |
| Validation check | Test, contract, and policy evidence | Validation finding | Cannot repair or bypass failures. |
| Release review | Compatibility, security, and sign-off evidence | Release recommendation | Cannot publish or tag a release. |

## Human-in-the-loop

The pipeline emits `ready`, `needs_review`, `blocked`, or `unknown` as an
advisory state. A human remains responsible for review completion and approval.
The existing domain StateMachine alone validates actual Page transitions.

## Traceability

Each finding should reference policy revision, evidence source, reviewer role,
timestamp, scope, and decision rationale. The design treats missing provenance
as a finding rather than accepting untrusted evidence.

## v5.6 standardized review gate

Production Pipeline v1 observes the existing `QualityChecked` artifact as the
completed quality-review evidence for one Page. It may mark approval as eligible
only when that evidence is present and `approve` is the next legal StateMachine
command. It never performs the approval, replaces a reviewer, or changes the
workflow context.

This keeps review integrated with Story, Character, Page, Art, and Export
readiness reports while preserving the human approval boundary.
