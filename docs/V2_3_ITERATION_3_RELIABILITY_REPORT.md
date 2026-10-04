# v2.3 Iteration 3 Reliability Report

## Scope

Iteration 3 prepares v2.3 RC quality without changing the Core Architecture,
page state machine, workflow semantics, repository port, provider/backend
protocols, or existing CLI/MCP contracts. No provider, image backend, cloud
monitoring system, distributed workflow, real-time monitor, or marketplace was
introduced.

## Reliability and recovery

- `WorkflowRecovery` remains page-scoped: it loads one persisted page, executes
  only the next legal Engine step, and saves only on success.
- `RepositoryRecovery` validates aggregate integrity before normal work resumes.
- Provider/backend failures are contained as local lifecycle health evidence;
  diagnostics never generate content or change page state.
- Existing sequential Batch resume/retry, notification retry, automation
  recovery, and Plugin/Extension isolation contracts remain covered by the
  regression suite.

## Runtime health and diagnostics

- `RuntimeHealthReport` is a presentation-independent DTO covering Provider,
  Backend, Repository, Workflow, Configuration, Plugin, Extension, and System
  health. JSON and Markdown rendering are available.
- `RuntimeDiagnostics` now includes provider, backend, and workflow report
  sections while retaining all prior fields.
- `RepositorySelfCheck` runs bounded, read-only aggregate/history/metadata/
  snapshot validation through the unchanged `ProjectRepository` interface.
- CLI additions: `health summary`, `repository check`, `provider check`, and
  `backend check`. Existing diagnostics commands remain compatible.
- MCP additions: `health_summary`, `provider_health`, `backend_health`, and
  `repository_check`. They return DTOs only.
- An optional FastAPI delivery composition exposes `/health`,
  `/health/providers`, `/health/backends`, `/diagnostics`, and
  `/repository/check` when the `api` extra is installed. The DTO application
  service remains testable without a web framework.

## Validation evidence

- Ruff: passed.
- mypy: passed for 189 source/test/benchmark files.
- pytest: passed, including compatibility, recovery, CLI, MCP, documentation
  link, runtime health, repository integrity, and repeatability tests.
- Repeatability smoke (`runs=5`, mock/local only):
  - Workflow spread: `0.3154`
  - Repository spread: `0.1377`
  - Provider lifecycle spread: `1.3456`
  - Backend lifecycle spread: `1.8515`
  - Configuration governance spread: `0.0907`

All remain inside the deliberately broad `<= 2.0` relative-spread smoke bound,
which detects pathological variance without imposing a machine-specific SLO.

## Architecture and compatibility review

| Boundary | Result |
| --- | --- |
| Core and Workflow | Unchanged. Health/diagnostics cannot transition a page or bypass approval. |
| Repository | `ProjectRepository` is unchanged; self-check uses only the port. |
| Providers and backends | Protocols unchanged; checks do not issue external calls. |
| Delivery | CLI/MCP add commands/tools only; FastAPI remains an optional outer adapter. |
| Public compatibility | Existing DTO fields and commands remain available; added report fields are additive. |

## Deferred work

- Remote provider/backend probes, external exporters, alerting, and cloud
  monitoring require a dedicated, credential-safe design.
- Automatic repository repair and distributed recovery are intentionally out of
  scope.
- FastAPI endpoint execution belongs to the optional `api` dependency test job;
  the default mock-only test suite does not install web dependencies.
