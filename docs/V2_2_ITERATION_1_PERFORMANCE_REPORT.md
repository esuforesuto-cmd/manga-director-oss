# v2.2 Iteration 1 Performance Report

## Outcome

Iteration 1 improves large-Project read/write behavior, sequential Batch
operability, and performance diagnostics without changing Core Architecture,
the `ProjectRepository` required interface, public workflow semantics, or the
package version (`2.1.0`).

## Delivered improvements

| Area | Improvement | Compatibility result |
| --- | --- | --- |
| Repository | Optional metadata listing, per-page selective read, paginated history read, and local metadata index | Existing `ProjectRepository` methods and callers are unchanged. |
| Database | Composite page indexes, metadata pagination, selective page/history queries, pool pre-ping for non-SQLite engines, and incremental child reconciliation | SQLite/PostgreSQL adapters retain their Repository contract. |
| Workflow | Shallow structural context transitions avoid deep-copying retained artifacts | Legal transitions, events, and one-page execution stay unchanged. |
| Batch | Execution statistics, progress snapshot, resume checkpoint, retry summary, and reused dependency set | Sequential-only policy remains enforced. |
| Observability | Bounded duration summaries, workflow timeline summaries, repository/database/batch metric names, and threshold warnings | Observers remain passive and optional. |

## Benchmark scenarios

The following provider-free scenarios are executable under `benchmarks/`:
`large_project`, `repository_index`, `database_query`, `batch_resume`, and
`workflow_scale`. The regression suite uses a conservative v2.1 smoke baseline
and fails only on a material slowdown.

## Verification

- Large Project, selective Repository, Database pagination, Batch checkpoint,
  retry summary, Workflow scale, observability warning, and performance
  regression tests pass.
- Existing unit, integration, contract, architecture, compatibility, security,
  and benchmark-smoke tests continue to pass.
- Full suite: 126 passing tests and 84.63% branch coverage (80% gate).
- Ruff and strict mypy pass for source, tests, and benchmarks; wheel/sdist and
  the index migration also complete successfully.

## Constraints retained

No asynchronous or parallel Workflow was added. No new provider, database,
Plugin, UI, FastAPI/OpenAPI, or Automation runtime was added. Image generation
still requires a persisted storyboard, approval still requires quality review,
and every workflow execution remains page-scoped.

## Architecture difference review

- **Ports:** the required `ProjectRepository` interface is unchanged. The new
  query helpers are an optional, separate capability implemented only by the
  bundled repositories.
- **Core workflow:** `Director`, `WorkflowEngine`, StateMachine, Agent ordering,
  event semantics, and page-at-a-time invariants are unchanged. Context copying
  is reduced only after copying the containers modified by a transition.
- **Infrastructure:** local sidecars and SQLAlchemy indexes stay within
  repository adapters. The performance monitor and repository metrics remain
  optional observers and do not control workflow decisions.
- **Batch:** the existing sequential worker model remains the only executable
  policy; statistics and checkpoints are persisted metadata, not a new
  execution path.

## Follow-up

Use [Performance Tuning](PERFORMANCE_TUNING.md) and the continuing items in
[Technical Debt](TECH_DEBT.md) to turn real workload measurements into v2.2
Issues. PostgreSQL production profiling, cache invalidation, and parallel work
remain deferred until separately approved.
