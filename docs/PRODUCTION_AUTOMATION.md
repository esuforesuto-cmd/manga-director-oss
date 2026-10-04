# Production Automation Intelligence

`V43ProductionIntelligenceService.production_automation()` creates a
read-only Production Plan, Stage Automation, Workflow Template, Schedule, and
Production Report from the v4.3 Production Pipeline Foundation. The name
"automation" describes analysis of a future plan; no automation is enabled.

| DTO | Planning purpose | Disabled boundary |
| --- | --- | --- |
| `ProductionPlanDTO` | Identifies one-Page production evidence and current state. | Applying a plan or changing workflow state. |
| `StageAutomationDTO` | Shows a proposed stage and its disabled automation status. | Starting/completing a stage or dispatching work. |
| `WorkflowTemplateDTO` | Describes StateMachine-governed template evidence. | Applying a template or skipping stages. |
| `ProductionScheduleDTO` | Presents an optional proposed window. | Registering a schedule or automatic start. |
| `ProductionReportDTO` | Combines the evidence for human review. | Any automatic action. |

The StateMachine remains authoritative. Each plan addresses exactly one Page,
and a persisted storyboard before image generation plus completed quality review
before approval remain mandatory.
