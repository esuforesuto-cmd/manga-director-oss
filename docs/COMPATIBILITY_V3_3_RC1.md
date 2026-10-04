# v3.3.0 RC1 Compatibility Audit

`3.3.0rc1` is additive over v3.2 and preserves documented v1.x through v3.2
contracts. v3.3 Foundation, Intelligence, and Governance services consume
existing Application DTO and Repository boundaries; they do not replace a
public port or workflow behavior.

| Surface | RC1 result |
| --- | --- |
| Python API | Existing root exports, typed DTOs, errors, and version import are retained; v3.3 modules are additive. |
| CLI / FastAPI / REST / MCP | Existing commands, routes, and DTO-only delivery boundaries remain; v3.3 paths are additive. |
| Workflow / Repository | One-Page StateMachine rules, persisted-storyboard-before-generation, quality-before-approval, and the Repository port are unchanged. |
| Knowledge / Creative / Asset / Analytics / Review / Diagnostics / Reporting / Governance | Existing APIs remain; v3.3 services are read-only projections. |
| Plugin / Extension SDK | Registry, manifest, lifecycle, context, and compatibility boundaries are unchanged. |
| Provider / Image Backend | Protocol and factory boundaries are unchanged; RC reports do not invoke either. |
| Automation / Notification / Health | Existing Application boundaries remain unchanged. |

The canonical package source is `3.3.0rc1`; MCP and optional OpenAPI derive it,
the frontend uses `3.3.0-rc.1`, and the SBOM matches it. No migration or
breaking change was identified.
