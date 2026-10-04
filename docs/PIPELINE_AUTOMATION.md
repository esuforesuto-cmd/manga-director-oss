# Pipeline Automation

Pipeline Automation is a safe semi-autonomous **planning** surface: every
stage is disabled until a separate human-approved implementation is introduced.
It does not start a stage, dispatch work, create an artifact, persist results,
or alter a workflow.

| DTO | Purpose | Disabled boundary |
| --- | --- | --- |
| `PipelineDefinitionDTO` | Declares a one-Page pipeline shape. | Persistence and execution. |
| `PipelineStageDTO` | Defines a StateMachine-revalidation stage. | Start and completion. |
| `StageResultDTO` | Represents a `not_run` result. | Artifact creation and workflow change. |
| `AutomationRuleDTO` | Describes a human-approved trigger. | Enforcement and automatic dispatch. |
| `PipelineSummary` | Counts only planned stages. | Automatic action. |

Any future pipeline action must verify one-Page scope, legal StateMachine
transition, persisted storyboard before image generation, and completed quality
review before approval.
