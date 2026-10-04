# Enterprise Diagnostics

`EnterpriseDiagnostics` composes presentation-independent DTOs for the local
system, configuration governance, one-page workflow analysis, Provider
optimization, image-backend inventory, and Repository maintenance.

The report contains audit findings and a compact `EnterpriseSummary`; it does
not expose secret values, execute workflow steps, call a Provider, generate an
image, repair Repository data, or invoke a delivery framework.

CLI, FastAPI composition, and MCP composition receive this report through
injected callbacks. The optional delivery endpoints/tools expose DTO data only:

- CLI: `manga-director analytics enterprise PROJECT PAGE`
- FastAPI: `GET /analytics/enterprise`
- MCP: `enterprise_diagnostics`

