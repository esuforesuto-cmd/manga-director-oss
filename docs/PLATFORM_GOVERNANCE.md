# Platform Governance

## v3.5 scope

Platform Governance is a local, read-only review projection. It combines the
existing Platform Analytics DTO with `PlatformPolicyDTO`, `PlatformAuditDTO`,
`PlatformComplianceReport`, and `PlatformGovernanceSummary`. It makes the
Enterprise boundary visible without adding Cloud monitoring, telemetry
retention, policy enforcement, release authorization, or external actions.

## Delivery surfaces

- CLI: `director platform-governance-v35 --project <id>`
- FastAPI: `GET /v3.5/platform-governance`
- MCP: `platform_governance_v35`

All surfaces return DTO data only. Policy storage, durable audit sinks,
identity controls, enforcement, and role-based authorization remain deferred
and require separately approved architecture.

