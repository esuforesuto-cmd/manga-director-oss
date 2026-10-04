# v4.0.0 RC1 Compatibility Audit

`4.0.0rc1` is additive over v3.5. The v4 Foundation, Intelligence, and
Governance services consume existing `WorkflowContext` and Repository
boundaries; they neither replace a public port nor change workflow behavior.

| Surface | RC1 result |
| --- | --- |
| Python API | Existing exports, typed DTOs, errors, and version import are retained; v4 services are additive. |
| CLI / FastAPI / REST / MCP | Existing commands, routes, metadata, and DTO-only delivery boundaries remain unchanged. |
| Workflow / Repository | One-page StateMachine rules, persisted-storyboard-before-generation, quality-before-approval, and the Repository port are unchanged. |
| Workspace / Memory / Graph / Quality | New modules are local, read-only projections with no persistence, enforcement, repair, execution, generation, or approval authority. |
| Plugin / Extension SDK | Registry, manifest, lifecycle, context, and compatibility boundaries are unchanged. |
| Web UI | Existing frontend API contracts remain; v4 adds no UI mutation or workflow control. |

The canonical package source is `4.0.0rc1`; MCP and optional OpenAPI derive
it, while the frontend uses `4.0.0-rc.1`. No migration or breaking change was
identified by the local RC suite.
