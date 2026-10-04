# Adaptive Planning

Adaptive Planning prepares a reviewable revision proposal; it does not adapt a
live plan or execute a decision. Planning sessions remain unstarted and local.

| DTO | Purpose | Disabled boundary |
| --- | --- | --- |
| `PlanningSessionDTO` | One-Page planning context. | Session start and persistence. |
| `ExecutionPlanRevisionDTO` | Rationale for a human-reviewed revision. | Revision application or workflow change. |
| `TaskPrioritizationDTO` | Fixed review, legality, and one-Page priority basis. | Automatic prioritization or dispatch. |
| `DependencyResolverDTO` | Identifies dependencies requiring human resolution. | Resolution and StateMachine bypass. |

Planning recommendations cannot skip a workflow stage, generate an image,
complete review, approve a Page, or coordinate multiple Pages.
