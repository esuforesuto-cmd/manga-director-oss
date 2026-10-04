# Goal Management

Goal Management provides immutable, human-owned one-Page goal evidence. It does
not register goals, create a hierarchy, complete a milestone, persist progress,
or select or approve work autonomously.

| DTO | Purpose | Disabled boundary |
| --- | --- | --- |
| `GoalManagerDTO` | Associates one goal with an advisory manager identity. | Registration and autonomous goal selection. |
| `GoalHierarchyDTO` | Describes an optional child-goal relationship. | Persistence and multi-Page scope. |
| `MilestoneDTO` | Defines a pending milestone for one Page. | Completion and persistence. |
| `ProgressEvaluationDTO` | Shows a local zero-progress evaluation. | Automatic action or retention. |
| `GoalSummary` | Reports prepared goal counts. | Autonomous decision-making. |

The `GoalDTO` one-Page constraint remains mandatory, and each later action must
continue to use the existing StateMachine and human-review boundaries.
