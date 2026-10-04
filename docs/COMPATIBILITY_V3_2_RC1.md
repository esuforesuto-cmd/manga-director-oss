# v3.2.0 RC1 Compatibility Audit

`3.2.0rc1` is additive over v3.1 and preserves the documented v1.x through
v3.1 contracts. v3.2 services are optional Application DTO consumers; they do
not replace public ports or workflow behavior.

| Surface | RC1 result |
| --- | --- |
| Python API | Existing root exports, typed DTOs, errors, and version import are retained; v3.2 modules are additive. |
| CLI / FastAPI / REST / MCP | Existing commands, routes, and DTO-only delivery boundaries remain; v3.2 paths are additive. |
| Workflow / Repository | One-Page StateMachine rules, persisted-storyboard-before-generation, quality-before-approval, and the Repository port are unchanged. |
| Knowledge / Creative / Asset / Analytics / Review / Diagnostics / Reporting | Existing APIs remain; v3.2 services are read-only projections. |
| Plugin / Extension SDK | Registry, manifest, lifecycle, context, and compatibility boundaries are unchanged. |
| Provider / Image Backend | Protocol and factory boundaries remain unchanged; RC reports do not invoke either. |
| Automation / Notification / Health | Existing Application boundaries remain unchanged. |

The canonical package source is `3.2.0rc1`; MCP and optional OpenAPI derive it,
the frontend uses `3.2.0-rc.1`, and the SBOM matches it. No migration or
breaking change was identified.
