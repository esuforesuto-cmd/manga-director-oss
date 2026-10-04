# Release Quality

Release Quality aggregates diagnostic quality evidence, stable compatibility
surfaces, non-enforcing quality gates, a baseline-only regression summary,
production validation, and a human release recommendation.

The result does not compare releases automatically, enforce a gate, publish an
artifact, or authorize a release. A human must still follow the existing release
process and hosted CI controls.

## Delivery

- CLI: `manga-director director release-quality --project <id> --page <n>` and
  `director compatibility-validation`
- FastAPI: `GET /v3.1/release-quality` and
  `GET /v3.1/compatibility-validation`
- MCP: `release_quality` and `compatibility_validation`

See [the example](../examples/release_quality/run.py).
