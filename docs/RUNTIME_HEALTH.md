# Runtime Health

The runtime uses local, isolated probes: repository reads, configuration
governance checks, plugin/extension diagnostics, and local provider/backend
construction. It does not issue network requests, generate images, or execute
workflow stages while collecting health.

Optional FastAPI delivery is available through the `api` extra and exposes only
DTO routes: `/health`, `/health/providers`, `/health/backends`, `/diagnostics`,
and `/repository/check`. The MCP surface exposes the matching
`health_summary`, `provider_health`, `backend_health`, `diagnostics_report`,
and `repository_check` tools. `health_status` remains a compatibility alias.
