# v4.0.0 Compatibility Verification

v4.0.0 is additive over v3.5. It preserves documented v1.x through v3.5.x
contracts while adding optional read-only Creative Workspace, Memory, Graph,
Quality, Intelligence, and Governance DTOs.

| Surface | Result |
| --- | --- |
| Python API | Existing exports, typed DTOs, errors, and version import remain; v4 is additive. |
| CLI / FastAPI / REST / MCP | Existing commands, routes, and DTO-only delivery boundaries remain unchanged. |
| Workflow / Repository | One-page StateMachine rules, persisted-storyboard-before-generation, quality-before-approval, and Repository ports are unchanged. |
| Workspace / Memory / Graph / Quality | New reports are local, read-only projections with no persistence, enforcement, repair, execution, generation, or approval authority. |
| Plugin / Extension SDK | Manifest, lifecycle, registry, context, and compatibility boundaries are unchanged. |
| Web UI | Existing frontend API contracts remain; v4 adds no UI mutation or workflow control. |

No migration or breaking change was identified.
