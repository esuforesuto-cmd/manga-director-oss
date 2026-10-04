# v2.4 Iteration 1 Production Runtime Report

## Outcome

Iteration 1 adds a small, optional Production Runtime at the Application and
Observability boundary. The Core architecture, Page `WorkflowEngine`,
StateMachine, Agents, Repository port, and existing delivery APIs were not
changed. The package version remains `2.3.0` as required for the development
branch.

## Delivered

- `ProductionRuntime` performs injected startup validation, local Provider and
  Image Backend warmup, readiness/liveness evaluation, and graceful shutdown.
- Immutable, transport-neutral `StartupReport`, `ShutdownReport`,
  `ProductionHealthReport`, `ProductionMetricsReport`, and
  `ProductionRuntimeReport` provide JSON and Markdown diagnostics.
- `ProductionMetrics` categorizes existing in-process metrics into startup,
  runtime, workflow, repository, provider, backend, automation, notification,
  and performance evidence.
- Provider and Backend runtimes support metadata/capability refresh, local
  warmup, deterministic priority evaluation, and a declarative-only fallback
  simulation. No provider or backend interface changed and no generation path
  is invoked.
- Provider-free benchmarks, runnable examples, operating documentation, and
  Production quality gates were added.

## Architecture review

| Concern | Result |
| --- | --- |
| Responsibility separation | Production runtime only coordinates injected Application/Observability probes. It contains no workflow, state-transition, or Agent logic. |
| Dependency direction | `production` depends on adapter/observability DTO boundaries; it does not import CLI configuration or concrete Repositories. |
| Workflow invariants | No Production Runtime method creates a Page, executes a step, publishes a workflow event, approves work, or generates an image. Existing StateMachine enforcement is unchanged. |
| Provider/Image boundary | Warmup constructs registered adapters and records lifecycle health only. Fallback is a disabled design DTO, not runtime selection. |
| Presentation boundary | Reports are Pydantic DTOs with JSON/Markdown helpers. No FastAPI, MCP, CLI, or Web UI dependency was added. |
| Public API compatibility | Root exports and existing APIs are unchanged. The optional package is imported explicitly as `manga_director.production`. |

There is no Architecture.md deviation: the addition is an outer Application /
Observability layer and preserves the existing inward dependency direction.

## Validation evidence

| Check | Result |
| --- | --- |
| Ruff | Passed for `src`, `tests`, `benchmarks`, and new examples. |
| mypy | Passed for `src`, `tests`, and `benchmarks` (197 source files). |
| pytest / coverage | Passed: 164 tests; total coverage 86.24% (required minimum: 80%). |
| Benchmarks | `startup_time`, `provider_warmup`, `configuration_reload`, `health_check`, and `runtime_metrics` completed without network access. |
| Examples | Production runtime, startup validation, health monitoring, provider warmup, and runtime report examples executed with mock/local boundaries. |
| Package build | Wheel and sdist for `manga-director 2.3.0` built successfully. |

## Scope confirmation

Not implemented: new Provider or Backend integrations, real fallback execution,
cloud monitoring, distributed runtime, Marketplace work, Core redesign, or
breaking public API changes.

## Follow-up evidence

The technical-debt register retains deployment-specific signal handling,
production database probes, external metrics export, remote health checks,
alert routing, and real provider fallback as explicitly deferred work. Each
requires an Issue with compatibility, security, benchmark, rollback, and
documentation evidence before implementation.
