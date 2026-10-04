# v3.1.0 RC1 Compatibility Verification

`3.1.0rc1` is additive over v3.0 and preserves v1.x through v3.0 contracts.
New v3.1 services are optional Application DTO consumers; they do not replace
or modify existing ports or workflow behavior.

| Surface | Verification |
| --- | --- |
| Python API | Root exports, typed DTOs, errors, and canonical version import remain stable. |
| CLI / FastAPI / REST / MCP | Existing commands, routes, and DTO-only delivery boundaries remain; v3.1 paths are additive. |
| Workflow / Repository | One-Page StateMachine rules, persisted-storyboard-before-generation, quality-before-approval, and Repository port are unchanged. |
| Knowledge / Creative / Review / Operations / Diagnostics / Reporting | Existing APIs remain; v3.1 diagnostics are read-only DTO projections. |
| Plugin / Extension SDK | Registry, manifest, lifecycle, context, and compatibility contracts are unchanged. |
| Provider / Image Backend | Protocol/Factory boundaries remain unchanged; RC reports never invoke either. |
| Automation / Notification / Health | Existing Application boundaries remain unchanged. |

The canonical package source is `3.1.0rc1`; MCP and optional OpenAPI derive it,
the frontend uses `3.1.0-rc.1`, and the SBOM matches it. No migration or
breaking change was identified.
