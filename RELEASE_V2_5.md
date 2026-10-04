# manga-director v2.5.0

## What's New

v2.5.0 promotes the reviewed Production quality, observability, diagnostics,
reliability, release-readiness, and OSS-readiness work to a stable release.
It introduces no workflow stage, Provider, Image Backend, Cloud service,
Marketplace, distributed runtime, Core redesign, or breaking change.

## Production Improvements

Application-layer startup, shutdown, health, repository integrity,
configuration validation, recovery admission, and readiness helpers remain
transport-neutral and do not execute workflow steps.

## Observability and Diagnostics Improvements

Workflow and operation timelines, metrics, diagnostic summaries, performance
analysis, operations plans, and executive DTOs are available without coupling
to a presentation framework or external monitoring system.

## Reliability and Release Quality Improvements

Read-only workflow, repository, configuration, recovery, long-running, version,
artifact, documentation, migration, and release checklist validation provide
local release evidence. These controls do not repair, publish, or mutate data.

## OSS Improvements and Developer Experience

Contribution, governance, license, dependency-license, community, supported
version, CI, typed API, examples, benchmark, package, and release-process
documentation are aligned for continued open-source maintenance.

## Performance Improvements

Provider-free benchmark smoke covers workflow, repository, Provider/Backend
runtime, automation, notification, diagnostics, reporting, health,
configuration, and release-readiness paths. It is local smoke evidence, not a
production SLO.

## Compatibility

v1.x and v2.0.x-v2.4.x Python API, CLI, FastAPI DTO, MCP, Workflow,
Repository, Plugin API, Extension SDK, Provider API, Image Backend API,
Automation, Notification, Diagnostics, Reporting, and Health contracts are
retained. See [Compatibility v2.5](docs/COMPATIBILITY_V2_5.md).

## Migration

No application-code migration is required from v2.4.x. Upgrade the package,
retain existing configuration and Project data, then run the read-only
repository and release validations. See [Migration v2.5](docs/MIGRATION_V2_5.md).

## Known Limitations

- Provider and Image Backend non-mock transports remain API-boundary stubs.
- FastAPI remains a DTO-only observability adapter, not a workflow REST API.
- Cloud monitoring, distributed runtime, remote plugin delivery, Marketplace,
  and automated deployment/release publication remain out of scope.

## Roadmap v2.6

v2.6 planning will remain Issue-driven and require compatibility, security,
benchmark, documentation, and rollback evidence before implementation. It will
not implicitly authorize a Core redesign or distributed workflow.

## GitHub Release body

Use this document as the GitHub Release body for tag `v2.5.0` after hosted CI,
dependency/CVE audit, secret scan, and publication checks succeed.
