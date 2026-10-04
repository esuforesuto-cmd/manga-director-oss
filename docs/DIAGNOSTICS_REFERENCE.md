# Diagnostics Reference

`ReliabilityDiagnostics` returns a transport-neutral DTO with the following
sections:

- architecture: Core isolation, one-page workflow scope, and StateMachine ownership;
- dependencies: supplied boundary readiness checks;
- plugins and extensions: supplied safe diagnostic summaries;
- providers and backends: metadata, capability, local health, and compatibility evidence;
- configuration: snapshot and governance evidence;
- workflow and repository: supplied read-only summaries.

`RuntimeStabilityReport` adds task lifecycle, memory, batch, and graceful
recovery evidence. `ProductionReadinessReport` adds deployment, upgrade, backup,
and recovery checklists. All reports provide `to_json()` and `to_markdown()` and
contain no presentation-layer models or workflow-control methods.

## v2.5 Iteration 2 additions

`ProductionInsights` adds a transport-neutral `DiagnosticsReport` with System,
Repository, Workflow, Provider, Backend, Configuration, Environment, and
Performance sections. It renders JSON or Markdown from safe snapshots only.
It is observational: no diagnostic operation runs an Agent, calls a provider,
or mutates a persisted Project.
