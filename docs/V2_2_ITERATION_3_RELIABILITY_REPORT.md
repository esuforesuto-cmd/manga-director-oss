# v2.2 Iteration 3 Reliability Report

## Outcome

Iteration 3 improves reliability, operational diagnostics, and performance
stability for the v2.2 RC path without changing the Core Architecture, required
Repository port, Workflow semantics, or the v2.2 release-candidate contract
(`2.2.0rc1`).

## Delivered

| Area | Improvement | Compatibility result |
| --- | --- | --- |
| Workflow recovery | Page-step recovery saves only after a successful Engine result | StateMachine, page-at-a-time execution, and persisted Context format are unchanged. |
| Repository recovery | Read-only integrity reports validate Project, metadata/history, and Batch snapshots | `ProjectRepository` methods are unchanged. |
| Batch/Database/Notification | Existing checkpoint/retry, transaction rollback, atomic local writes, and bounded notification retry are documented and regression-tested | No new execution policy or persistence driver was introduced. |
| Plugin/Extension isolation | Plugin lifecycle rollback and Extension load error isolation remain outside Workflow control flow | Plugin/SDK contracts are unchanged. |
| Health/Diagnostics | System Health Dashboard and Runtime Diagnostic DTOs support CLI/MCP plus JSON/Markdown output | DTOs are transport-neutral and expose no internal runtime models. |
| Performance stability | Five provider-free repeatability benchmark scenarios detect pathological variance | No cross-machine throughput SLO is imposed. |

## Baseline boundary

This source baseline has no FastAPI or Automation runtime. Therefore no HTTP
server was introduced in this quality iteration. `SystemHealthDashboard` and
`RuntimeDiagnosticReport` are the reviewed DTO boundary for a future adapter;
existing MCP tools expose the same safe data.

## Verification

- Full suite: 138 passing tests and 85.11% branch coverage (80% gate).
- Ruff and strict mypy pass for source, tests, and benchmarks.
- Health, recovery, integrity, diagnostics CLI/MCP, and repeatability benchmark
  tests pass; the new examples and wheel/sdist package build also pass.

## Architecture difference review

- Domain StateMachine, Agent ordering, WorkflowEngine, Director coordination,
  and one-page invariants are unchanged.
- Reliability helpers depend on existing WorkflowEngine/ProjectLoader and
  `ProjectRepository` ports; they do not know LocalFile or Database adapters.
- Health and diagnostic models are in Observability and do not depend on CLI,
  MCP, or any Presentation framework.
- No asynchronous/distributed runtime, Provider, Plugin, Database, Workflow, or
  breaking public API was added.
