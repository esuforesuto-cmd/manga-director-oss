# manga-director v2.6.0

## What's New

v2.6.0 promotes the reviewed RC1 as the stable AI Workflow Ready release. It
adds no workflow stages, live provider, image backend, cloud service, or
breaking public API change.

## AI Workflow Improvements

Read-only workflow planning, execution previews, dependency graphs, complexity
analysis, validation, consistency, risk, and readiness reports are available in
the optional Application layer. They do not execute an Agent or change state.

## Workflow Intelligence Improvements

Workflow analysis provides critical-path, bottleneck, comparison, trend, and
optimization-recommendation DTOs. `WorkflowEngine` and the StateMachine remain
the only execution and transition authorities.

## Provider Governance Improvements

Provider metadata, capability, lifecycle, policy, compatibility, risk, and
recommendation reports remain Protocol- and Factory-based. No provider-specific
behavior leaks into Workflow, Agent, or CLI code.

## Enterprise and Production Improvements

Enterprise Readiness, configuration evidence, repository integrity, recovery,
health, observability, diagnostics, reporting, and executive dashboard DTOs
support safe local operation without a Cloud or distributed-runtime dependency.

## Performance and Developer Experience

Provider-free benchmark smoke covers workflow, repository, planning, analysis,
runtime, automation, diagnostics, reporting, and health. Typed APIs, examples,
quality gates, package checks, and frontend validation remain available.

## Compatibility and Migration

v2.6.0 is backward compatible with v1.x and v2.0.x-v2.5.x public contracts.
No Project, configuration, workflow, Repository, Plugin, Extension SDK,
Provider, or Image Backend data migration is required. See
[Migration](docs/MIGRATION_V2_6.md) and [Compatibility](docs/COMPATIBILITY_V2_6.md).

## Known Limitations

Non-mock adapters, autonomous AI, Cloud monitoring, marketplace, and
distributed runtime remain out of scope. Planning and recommendation services
are diagnostic-only; they never auto-execute or auto-approve a Page.

## Roadmap v2.7

v2.7 planning will remain issue-driven and preserve the v2 architecture. It may
consider validated operational and ecosystem improvements only after an
architecture and compatibility review.

## GitHub Release Body

Use this document as the GitHub Release body for tag `v2.6.0` after hosted CI,
security scans, and publication checks complete on the release tag.
