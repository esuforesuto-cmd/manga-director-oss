# v3.2.0 Compatibility Verification

v3.2.0 promotes the reviewed RC1 evidence to stable metadata without a public
contract, workflow, or Repository-interface change. v1.x, v2.0.x-v2.7.x,
v3.0.x, and v3.1.x contracts are retained.

| Surface | Verification |
| --- | --- |
| Python API | Root exports, typed DTOs, errors, and the canonical version import are retained. |
| CLI / FastAPI / REST / MCP | Existing commands, routes, and DTO-only delivery boundaries remain; v3.2 paths are additive. |
| Workflow / Repository | One-Page StateMachine rules, persisted storyboard before generation, quality before approval, and the Repository port are unchanged. |
| Knowledge / Creative / Asset / Analytics / Review / Diagnostics / Reporting / Health | Existing APIs remain; v3.2 services are read-only DTO projections. |
| Plugin / Extension SDK | Registry, manifest, lifecycle, context, and compatibility contracts are unchanged. |
| Provider / Image Backend | Protocol and factory boundaries remain unchanged; reports do not invoke either. |
| Automation / Notification | Existing Application boundaries remain unchanged. |

Python, MCP, optional OpenAPI, frontend metadata, and SBOM derive `3.2.0` from
the canonical package version source. No migration or breaking change was
identified.
