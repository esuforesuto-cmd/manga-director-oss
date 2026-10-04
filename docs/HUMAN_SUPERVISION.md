# Human Supervision

Human Supervision provides immutable approval and intervention evidence for one
Page. It cannot request or grant approval, apply an intervention, grant an
override, bypass the StateMachine, or retain a supervision session.

| DTO | Purpose | Disabled boundary |
| --- | --- | --- |
| `SupervisionSessionDTO` | Relates one execution session to a human owner. | Session start and persistence. |
| `ApprovalCheckpointDTO` | Makes StateMachine, storyboard, and quality-review checks visible. | Approval request or grant. |
| `InterventionDTO` | Recommends human review. | Intervention and workflow change. |
| `OverrideRequestDTO` | Records a human-authorization-required proposal. | Submission, override, and bypass. |

No override can supersede one-Page scope, a legal StateMachine transition,
persisted storyboard before image generation, or completed quality review before
approval.
