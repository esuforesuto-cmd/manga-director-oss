# Long-running Task Foundation

v4.2 models a future long-running task as a non-executing, one-Page-scoped
planning projection. No queue, scheduler, background worker, retry loop,
continuation, cancellation, persistence, or concurrent execution is enabled.

| DTO | Purpose | Disabled boundary |
| --- | --- | --- |
| `TaskQueueDTO` | Proposed task-queue membership. | Dispatch and persistence. |
| `ScheduledTaskDTO` | Future scheduling descriptor. | Schedule registration and execution. |
| `BackgroundTaskDTO` | Background-work boundary declaration. | Worker start and long-running processing. |
| `TaskProgressDTO` | Initial progress view. | Progress retention and automatic continuation. |
| `TaskLifecycleSummary` | Planned lifecycle counts. | Running or completed task mutation. |

Long-running support must never widen one workflow execution beyond one Page or
allow a stage, storyboard, quality review, or approval boundary to be skipped.
