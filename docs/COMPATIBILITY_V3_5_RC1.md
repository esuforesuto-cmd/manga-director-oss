# v3.5.0 RC1 Compatibility Audit

`3.5.0rc1` is additive over v3.4. v3.5 Foundation, Intelligence, and
Governance services consume existing Application DTO, `WorkflowContext`, and
Repository boundaries; they neither replace a public port nor change workflow
behavior.

| Surface | RC1 result |
| --- | --- |
| Python API | Existing exports, typed DTOs, errors, and version import are retained; v3.5 modules are additive. |
| CLI / FastAPI / REST / MCP | Existing commands, routes, and DTO-only delivery boundaries remain; v3.5 paths are additive. |
| Workflow / Repository | One-Page StateMachine rules, persisted-storyboard-before-generation, quality-before-approval, and the Repository port are unchanged. |
| Knowledge / Creative / Production / Platform / Governance | Existing APIs remain; v3.5 services are local, read-only projections. |
| Plugin / Extension SDK | Registry, manifest, lifecycle, context, and compatibility boundaries are unchanged. |
| Web UI | Existing frontend API contracts remain; v3.5 adds no UI mutation or workflow control. |

The canonical package source is `3.5.0rc1`; MCP and optional OpenAPI derive
it, while the frontend uses `3.5.0-rc.1`. No migration or breaking change was
identified.
