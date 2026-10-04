# Platform Analytics Planning

Executive Dashboard, Cross Platform Analytics, Trend Analytics, Historical
Analytics, Regression Intelligence, and Platform Health are bounded aggregation
candidates. Inputs must be supplied locally, redacted where needed,
deterministic, and traceable to source evidence.

Analytics cannot collect externally, retain telemetry, operate a service,
authorize a release, or trigger an action. See [the v3.5 roadmap](ROADMAP_v3_5.md).

## Iteration 2

Cross Platform KPI, Historical Trend, Regression Trend, Executive Analytics,
and Platform Health Dashboard DTOs combine supplied Foundation evidence only.
They cannot persist a trend, collect remotely, start monitoring, enforce a KPI,
authorize a release, remediate, or trigger an external action.

- CLI: `manga-director director executive-analytics-v35 --project <id>`
- FastAPI: `GET /v3.5/executive-analytics`
- MCP: `executive_analytics_v35`
