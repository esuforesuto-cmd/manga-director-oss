# v3.3.0 Compatibility Verification

`3.3.0` is additive over v3.2 and preserves documented v1.x, v2.0.x-v2.7.x,
v3.0.x, v3.1.x, and v3.2.x contracts. v3.3 services consume existing
Application DTO and Repository boundaries; they replace no public port or
workflow behavior.

| Surface | Result |
| --- | --- |
| Python API | Existing root exports, typed DTOs, errors, and version import are retained; v3.3 modules are additive. |
| CLI / FastAPI / REST / MCP | Existing commands, routes, and DTO-only delivery boundaries remain; v3.3 paths are additive. |
| Workflow / Repository | One-Page StateMachine rules, persisted storyboard before generation, quality review before approval, and the Repository port are unchanged. |
| Knowledge / Creative / Asset / Analytics / Review / Diagnostics / Reporting / Governance / Health | Existing APIs remain; v3.3 surfaces are read-only projections. |
| Plugin / Extension SDK | Registry, manifest, lifecycle, context, and compatibility boundaries are unchanged. |
| Provider / Image Backend | Protocol and factory boundaries are unchanged; reports do not invoke either. |
| Automation / Notification | Existing Application boundaries remain unchanged. |

The canonical Python version is `3.3.0`; optional OpenAPI and MCP derive it,
the frontend uses `3.3.0`, and the SBOM matches it. No migration or breaking
change was identified.
