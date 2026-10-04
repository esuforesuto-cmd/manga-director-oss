# Checkpoint Management

Checkpoint DTOs provide reviewable evidence for a possible future pause/resume
flow. The local `CheckpointRepository` is immutable and caller-provided; it
does not replace or alter the existing Project Repository interface.

| DTO | Purpose | Disabled boundary |
| --- | --- | --- |
| `CheckpointDTO` | Workflow-state and artifact-reference checkpoint evidence. | Automatic checkpoint persistence or repair. |
| `SnapshotDTO` | Integrity-review snapshot descriptor. | Restoration or data mutation. |
| `ResumeRequestDTO` | Human-authorization-required resume proposal. | Dispatch and automatic resume. |
| `ResumeResultDTO` | Denied-by-default result projection. | Resume, transition, or persistence. |

A future resume must revalidate policy, configuration, checkpoint integrity,
one-Page scope, StateMachine legality, persisted storyboard, and quality-review
boundaries before any human-approved action is considered.
