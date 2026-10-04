# Observability Reference

`ProductionInsights` composes read-only Application-layer DTOs from the
existing `MetricsRegistry`, `WorkflowContext`, and `RepositoryMaintenance`.
It does not subscribe a new workflow listener, alter an EventBus, execute an
Agent, save a Project, invoke a Provider, generate an image, or use a network.

## Observability report

`ObservabilityReport` contains:

- a workflow timeline derived from persisted Context history;
- an operation timeline from caller-supplied observations;
- repository, Provider, Backend, Automation, and Release metric categories;
- a bounded performance snapshot of counters and duration summaries.

Metric names retain their existing prefixes. The report only groups snapshots;
it does not define a telemetry exporter or a Cloud monitoring protocol.
