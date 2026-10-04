# v3.1.0 Compatibility Verification

v3.1.0 promotes RC1 evidence to stable metadata without a public-contract or
workflow change. v1.x, v2.0.x-v2.7.x, and v3.0.x contracts are retained.

| Surface | Verification |
| --- | --- |
| Python API | Root exports, typed DTOs, errors, and canonical version import are retained. |
| CLI / FastAPI / REST / MCP | Existing commands, routes, and DTO-only delivery boundaries remain; v3.1 paths are additive. |
| Workflow / Repository | One-Page StateMachine rules, persisted storyboard before generation, quality before approval, and Repository port are unchanged. |
| Knowledge / Creative / Review / Operations / Diagnostics / Reporting / Health | Existing APIs remain; v3.1 services are read-only DTO projections. |
| Plugin / Extension SDK | Registry, manifest, lifecycle, context, and compatibility contracts are unchanged. |
| Provider / Image Backend | Protocol and Factory boundaries remain unchanged; reports do not invoke either. |
| Automation / Notification | Existing Application boundaries remain unchanged. |

Python, MCP, optional OpenAPI, frontend metadata, and SBOM derive `3.1.0` from
the canonical package version source. No migration or breaking change was
identified.
