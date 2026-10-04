# Production Readiness v3

Production Readiness composes workflow, Director, Knowledge, configuration,
and operational checklist DTOs. It validates readiness for human review only;
it does not deploy, start an operation, configure a service, or authorize a
release.

The Release Readiness dashboard groups Director, Creative, Knowledge, and
Production executive DTOs. `deployment_performed`, `release_authorized`, and
`automatic_release` remain false by design.

Delivery: `manga-director director production-readiness`, `director
release-dashboard`, `GET /v3/production-readiness`, `GET /v3/release-readiness`,
and MCP tools `production_readiness` / `release_readiness`.
