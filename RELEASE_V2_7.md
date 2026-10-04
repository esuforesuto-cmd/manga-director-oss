# manga-director v2.7.0

## What's New

v2.7.0 promotes the reviewed RC1 as the stable AI Director Foundation release.
It adds no workflow stage, live provider, image backend, Cloud service, or
breaking public API change.

## AI Director Foundation

Read-only Director planning provides a StateMachine-derived one-page strategy,
bounded public decision trace, dependency graph, readiness, integrity,
consistency, and reliability evidence. It never calls an Agent, executes a
command, transitions state, or authorizes approval.

## Knowledge Intelligence

Knowledge snapshots, summaries, searches, relationships, coverage,
consistency, governance, quality, and risk reports are repository-derived and
redacted. They expose metadata keys rather than values and preserve the
existing Repository port.

## Workflow Orchestration

Workflow plans, sequence previews, task grouping, analysis, optimization, and
diagnostics are visualization and recommendation DTOs. `WorkflowEngine` and
the StateMachine remain the sole execution and transition authorities.

## Enterprise AI and Production Improvements

Enterprise AI readiness, configuration evidence, repository integrity,
recovery, health, observability, diagnostics, reporting, and executive
dashboards support safe local operation without a Cloud or distributed-runtime
dependency.

## Performance and Developer Experience

Provider-free benchmark smoke covers Workflow, Repository, Knowledge, planning,
analysis, runtime, diagnostics, reporting, and health. Typed APIs, examples,
quality gates, package checks, and frontend validation remain available.

## Compatibility and Migration

v2.7.0 is backward compatible with v1.x and v2.0.x-v2.6.x public contracts.
No Project, configuration, workflow, Repository, Plugin, Extension SDK,
Provider, or Image Backend data migration is required. See
[Migration](docs/MIGRATION_V2_7.md) and [Compatibility](docs/COMPATIBILITY_V2_7.md).

## Known Limitations

Non-mock adapters, autonomous AI, Cloud monitoring, marketplace, and
distributed runtime remain out of scope. Director, Knowledge, planning, and
recommendation services are diagnostic-only; they never auto-execute or
auto-approve a Page.

## Roadmap v3.0

v3.0 remains a planning horizon. Any autonomous, Cloud, marketplace, or
distributed capability requires a separately approved architecture, trust,
security, compatibility, and operational model.

## GitHub Release Body

Use this document as the GitHub Release body for tag `v2.7.0` after hosted CI,
security scans, and publication checks complete on the release tag.
