# Creative Workspace 2.0

Creative Workspace 2.0 is a design for a unified, read-only view of an
existing production context. It is not a new collaboration database or a
workflow controller.

| Concept | Planned DTO responsibility | Boundary |
| --- | --- | --- |
| Unified Workspace | Group Project, Story, Character, Asset, process, and quality references. | Does not create or mutate any source record. |
| Workspace Session | Describe a human-selected working context. | Does not start an Agent or workflow execution. |
| Workspace State | Summarize existing StateMachine and review evidence. | Does not transition state. |
| Workspace Snapshot | Capture supplied evidence for deterministic review. | Does not persist a snapshot. |
| Workspace Timeline | Order existing events and reports. | Does not retain or schedule events. |

Migration begins with optional DTO projections behind Application services. Any
CLI, FastAPI, MCP, or Web UI exposure must be additive and preserve current
commands, routes, and user workflows.
