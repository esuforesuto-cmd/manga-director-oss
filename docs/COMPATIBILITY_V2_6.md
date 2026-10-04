# v2.6.0 Compatibility Verification

v2.6.0 promotes RC1 evidence to stable metadata without a public-contract or
workflow change. The following v1.x and v2.0.x-v2.5.x surfaces are retained:

| Surface | Verification |
| --- | --- |
| Python API | Root exports, typed DTOs, errors, and canonical version import are retained. |
| CLI / FastAPI / REST / MCP | Existing commands and DTO-only delivery boundaries are retained; OpenAPI and MCP metadata derive from the package version. |
| Workflow / Repository | One-page, forward-only workflow invariants and the Repository port are unchanged. |
| Plugin / Extension SDK | Registry, manifest, lifecycle, compatibility, context, and packaging contracts are unchanged. |
| Provider / Image Backend | Protocol and Factory contracts remain unchanged; v2.6 reports are metadata-only. |
| Automation / Notification | Existing Application-layer boundaries remain unchanged. |
| Planning / Diagnostics / Reporting / Health | Existing DTOs are retained; v2.6 advisory services are optional additive APIs. |

Python, MCP, optional OpenAPI, frontend metadata, and SBOM use `2.6.0` through
the canonical package version source. No migration or breaking change was
identified.
