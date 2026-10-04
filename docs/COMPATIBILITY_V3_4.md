# v3.4.0 Compatibility Audit

`3.4.0` is additive over v3.3 and preserves documented v1.x, v2.0.x-v2.7.x,
v3.0.x, v3.1.x, v3.2.x, and v3.3.x contracts.

| Surface | Result |
| --- | --- |
| Python API, Workflow, Repository | Preserved; no port or state-machine change. |
| CLI, FastAPI/REST, MCP | Preserved; v3.4 reports are optional additive commands, routes, and tools. |
| Knowledge, Creative, Asset, Analytics, Review | Preserved; new reports are read-only DTO projections. |
| Diagnostics, Reporting, Governance, Operations, Health | Preserved; no transport or presentation dependency was added. |
| Plugin, Extension SDK, Provider, Image Backend | Preserved; no interface or runtime contract changed. |
| Automation, Notification, configuration, database | Preserved; no schema, storage, or execution-policy migration is required. |

The package version is canonical in `manga_director._version`; `pyproject.toml`
derives its package value, while optional OpenAPI and MCP derive it at runtime.
The frontend and SBOM carry the equivalent stable value. No public API was
removed, renamed, or made stricter.
