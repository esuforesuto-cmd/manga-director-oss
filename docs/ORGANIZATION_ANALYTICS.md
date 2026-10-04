# Organization Analytics

Organization Analytics provides a bounded, redacted view of local one-Page
organization evidence: state/history observations, collaboration hand-offs,
role descriptors, and an explicitly non-computed forecast.

## Safety boundary

This is not personnel analytics. It does not calculate person or team scores,
collect external data, assign work, alter roles or membership, notify people,
commit delivery, or make operational changes. Human governance remains outside
this diagnostic capability.

## Delivery surfaces

- CLI: `manga-director director organization-analytics-v34 --project <id>`
- FastAPI: `GET /v3.4/organization-analytics`
- MCP: `organization_analytics_v34`

The response is the immutable `OrganizationAnalyticsDashboardDTO`.
