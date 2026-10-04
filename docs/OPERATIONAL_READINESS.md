# Operational Readiness

Operational Readiness provides DTO evidence for human review of operation,
deployment, configuration shape, environment, release readiness, and health.
It uses one supplied Page context and existing local reports only.

No deployment, external environment probe, configuration change, runtime
operation, or release authorization is available through this service.

## Delivery

- CLI: `manga-director director operational-readiness-v31 --project <id> --page <n>`
- FastAPI: `GET /v3.1/operational-readiness`
- MCP: `operational_readiness_v31`

See [the example](../examples/operational_readiness/run.py).
