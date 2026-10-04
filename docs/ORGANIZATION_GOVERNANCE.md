# Organization Governance

Organization Governance provides policy, compliance, audit, and summary DTOs
over bounded local organization evidence. It supports human review of role and
handoff observations without treating people as a control surface.

## Safety boundary

It does not collect external data, score people or teams, assign work, change
roles or membership, send notifications, persist an audit, or commit delivery.
All governance outcomes remain human decisions.

## Delivery surfaces

- CLI: `manga-director director organization-governance-v34 --project <id>`
- FastAPI: `GET /v3.4/organization-governance`
- MCP: `organization_governance_v34`

The DTO-only result is `OrganizationGovernanceDashboardDTO`.
