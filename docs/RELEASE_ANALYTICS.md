# Release Analytics

Release Analytics aggregates local version, compatibility-baseline, and
workflow-history evidence into an advisory trend, deployment, regression, and
forecast report. Hosted release validation remains a separate release process.

## Safety boundary

The report does not collect remote analytics, start a deployment, detect or
remediate a regression authoritatively, change public APIs, authorize a
release, create a tag, sign, or publish. It cannot replace compatibility or
release quality gates.

## Delivery surfaces

- CLI: `manga-director director release-analytics-v34 --project <id>`
- FastAPI: `GET /v3.4/release-analytics`
- MCP: `release_analytics_v34`

Each transport returns `ReleaseAnalyticsDashboardDTO` and no internal release
models.
