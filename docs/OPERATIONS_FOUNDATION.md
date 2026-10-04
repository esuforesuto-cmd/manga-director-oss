# Operations Foundation

Operations Foundation composes safe, in-process evidence for a selected
one-Page context. `ProjectMetrics`, `WorkflowMetrics`, `QualityMetrics`, and
`ReleaseMetrics` feed `OperationsSummary` and `OperationalHealthReport` DTOs.

The reports do not collect from a remote system, modify configuration, schedule
work, deploy software, approve a Page, or publish a release. They use the
existing Repository port only for aggregate counts.

## Delivery

- CLI: `manga-director director operations-foundation --project <id> --page <n>`
  and `director project-metrics`
- FastAPI: `GET /v3.1/operations` and `GET /v3.1/project-metrics`
- MCP: `operations_foundation` and `project_metrics`

See [Operations example](../examples/operations_foundation/run.py) and
[project metrics example](../examples/project_metrics/run.py).
