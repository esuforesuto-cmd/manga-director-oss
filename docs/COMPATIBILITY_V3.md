# v3.0.0 Compatibility Verification

v3.0.0 promotes RC1 evidence to stable metadata without a public-contract or
workflow change. The following v1.x and v2.0.x-v2.7.x surfaces are retained:

| Surface | Verification |
| --- | --- |
| Python API | Root exports, typed DTOs, errors, and canonical version import are retained. |
| CLI / FastAPI / REST / MCP | Existing commands and DTO-only delivery boundaries are retained; OpenAPI and MCP metadata derive from the package version. |
| Workflow / Repository | One-page, forward-only StateMachine invariants and the Repository port are unchanged. |
| Knowledge / Director / Planning / Creative / Review / Diagnostics / Reporting / Health | Existing DTOs are retained; v3 services are optional additive application APIs. |
| Plugin / Extension SDK | Registry, manifest, lifecycle, compatibility, context, and packaging contracts are unchanged. |
| Provider / Image Backend | Protocol and Factory contracts remain unchanged; v3 reports are metadata- and context-only. |
| Automation / Notification | Existing Application-layer boundaries remain unchanged. |

Python, MCP, optional OpenAPI, frontend metadata, and SBOM use `3.0.0` through
the canonical package version source. No migration or breaking change was
identified.
