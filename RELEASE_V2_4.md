# manga-director v2.4.0

## What's New

v2.4.0 formally releases the reviewed production-operation improvements from
the v2.4 cycle. It adds no page-workflow stage, changes no StateMachine rule,
and removes no supported public API.

## Production Runtime Improvements

- Startup validation, dependency validation, readiness/liveness evidence, and
  graceful shutdown sequencing are available as outer application services.
- Runtime configuration snapshots, comparisons, fingerprints, import
  validation, and safe export remain configuration-layer operations.

## Observability Improvements

- Transport-neutral runtime, workflow, repository, provider, backend,
  automation, notification, and startup metrics are available as DTOs.
- Health summaries and timeline-oriented diagnostics remain safe observation
  paths; they do not execute workflow steps or contact providers.

## Reliability Improvements

- Workflow resume validation, consistency checks, repository integrity scans,
  recovery simulations, and long-running stability summaries are additive and
  read-only until an existing workflow operation is explicitly invoked.

## Diagnostics Improvements

- Production, dependency, configuration, provider, backend, workflow,
  repository, plugin, extension, and architecture diagnostics support JSON or
  Markdown reporting without exposing internal mutable models.

## Enterprise Improvements

- Configuration governance, local profiles, redacted snapshots, repository
  port-based operations, provider/backend inventories, and health history are
  available for controlled local deployment.

## Performance Improvements

Provider-free benchmark smoke covers startup, workflow, repository, database,
batch, provider/backend runtime, notification, automation, Plugin, Extension,
configuration, diagnostics, recovery, and long-running paths. It does not
claim a production workload SLO.

## Developer Experience

Typed DTOs, examples, benchmarks, architecture and compatibility gates,
frontend checks, package validation, and release documentation are retained in
the release process.

## Compatibility

v1.x and v2.0.x-v2.3.x Python API, CLI, optional FastAPI DTO adapter, local
MCP, Workflow, Repository, Plugin API, Extension SDK, Provider API, Image
Backend API, Automation, Notification, Diagnostics, and Health contracts are
retained. See [the v2.4 compatibility verification](docs/COMPATIBILITY_V2_4.md).

## Migration

No migration is required. Existing project files, workflow states, repository
settings, Plugins, Extensions, and mock-only deployments continue to work.
See [the v2.4 migration guide](docs/MIGRATION_V2_4.md).

## Known Limitations

- Non-mock external Provider and Image Backend adapters remain intentional
  boundary stubs.
- FastAPI is an optional observability DTO adapter, not a workflow REST server
  or Web UI backend.
- Cloud monitoring, remote probes, distributed runtime, remote plugin delivery,
  and Marketplace capabilities remain out of scope.

## Roadmap v2.5

v2.5 planning remains issue-driven. Any provider/backend implementation,
production delivery, or remote operation requires a separate architecture,
security, compatibility, and migration review before implementation.

## GitHub Release Body

Use this document as the GitHub Release body for tag `v2.4.0` after hosted CI,
dependency/CVE and secret scans, and the publication checklist have succeeded.
