# Project Operations

Project Operations offers bounded analysis of an existing Project and one Page
context: milestone observations, declared-resource shape, non-committal
delivery assumptions, and current risks. It is suitable for human planning and
review, not for operating a Project.

The report never allocates resources, edits a schedule, starts an operation,
mitigates risk, commits delivery, or changes the workflow. Its forecast is
always explicitly `not_computed`.

The same immutable dashboard is exposed by `director project-operations-v33`,
`GET /v3.3/project-operations`, and MCP `project_operations_v33`.

## v4.3 Creative Production Platform design

The v4.3 planning cycle proposes additional Team Workspace, Task Board,
Progress Dashboard, KPI Framework, and Project Analytics DTOs. They consume
supplied evidence and provide human-reviewable observations only; they do not
change the existing v3.3 delivery surface or introduce a new transport route.

| Proposed record | Planning purpose | Prohibited behavior |
| --- | --- | --- |
| Team Workspace | Describe declared roles and collaboration context. | Creating members or changing permissions. |
| Task Board | Show supplied task and dependency evidence. | Assigning, dispatching, or completing tasks. |
| Progress Dashboard | Summarize declared milestone and Page evidence. | Mutating progress or workflow state. |
| KPI Framework | Define observable, redacted project measures. | Setting targets, alerts, or automated actions. |
| Project Analytics | Compare historical evidence and assumptions. | Forecasting commitments, allocating resources, or changing schedules. |

Any future v4.3 implementation remains additive to existing CLI, FastAPI, MCP,
Web UI, Repository, and Workflow contracts and requires explicit human review.
