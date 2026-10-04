# Operations Intelligence

Operations Intelligence is a one-Page DTO projection of existing Operations
Foundation evidence. It supplies workflow efficiency, project health, quality
trend, release-readiness metrics, insights, and a summary.

All measurements are local observations. They do not alter a workflow,
configuration, repository, runtime, release, or operational plan. Quality and
release fields remain evidence, never an authorization.

## Delivery

- CLI: `manga-director director operations-intelligence --project <id> --page <n>`
  and `director workflow-efficiency`
- FastAPI: `GET /v3.1/operations-intelligence` and
  `GET /v3.1/workflow-efficiency`
- MCP: `operations_intelligence` and `workflow_efficiency`

See [the example](../examples/operations_intelligence/run.py).
