# manga-director v2.3.0

## What's New

v2.3.0 formally releases the reviewed v2.3 improvements for enterprise
operation, provider/image-backend runtime introspection, repository
scalability, configuration governance, diagnostics, and reliability. It adds
no workflow stage and changes no existing public contract.

## Enterprise Improvements

- Configuration profiles, read-only controls, safe snapshots/diffs, schema
  compatibility, integrity assessment, and redacted fingerprints.
- Repository scalability helpers for compact indexes, bounded history reads,
  scans, and self-checks while retaining the base Repository protocol.
- DTO-only health and enterprise diagnostics for controlled local operation.

## Provider Runtime Improvements

Provider factories retain their registry API while adding discovery metadata,
capability/model reports, local lifecycle health, and safe diagnostics. Health
paths do not issue provider requests.

## Image Backend Runtime Improvements

Image backends retain the `ImageGenerator` contract while adding metadata
discovery, lifecycle health, preset/workflow validation, and diagnostics.
Health paths do not generate images.

## Performance Improvements

Provider-free benchmark and repeatability smoke coverage spans workflow,
repository, database, batch, plugin, extension, provider/backend runtime,
notification, automation, configuration, and diagnostics boundaries.

## Reliability Improvements

One-page workflow recovery, repository integrity/recovery, Batch resume/retry,
notification retry, Plugin/Extension isolation, health summaries, and
transport-neutral diagnostics are verified without changing StateMachine rules.

## Developer Experience

Typed DTOs, examples, benchmarks, architecture/compatibility gates, package
validation, optional FastAPI-extra verification, frontend gates, and release
documentation are included in the release process.

## Compatibility

v1.x, v2.0.x, v2.1.x, and v2.2.x Python API, CLI, local MCP, Workflow,
Repository, Plugin API, Extension SDK, Provider API, Image Backend API,
Notification, and Automation contracts are retained. See
[the v2.3 compatibility verification](docs/COMPATIBILITY_V2_3.md).

## Migration

No migration is required. Existing project files, workflow states, repository
configuration, Plugins, and Extensions remain compatible. Optional API use is
installed explicitly with `manga-director[api]`; it exposes observability DTOs
only, not workflow operations.

## Known Limitations

- Non-mock external Provider and Image Backend adapters remain intentional
  boundary stubs.
- FastAPI serves optional health/diagnostics DTOs only; it is not a workflow
  REST service or Web UI backend.
- Cloud monitoring, remote probes, distributed workflow, remote plugin
  delivery, and Marketplace functions remain out of scope.

## Roadmap v2.4

v2.4 planning will remain issue-driven. Candidate work includes production
workload evidence, remote adapter contracts, and delivery capabilities only
after separate architecture, security, compatibility, and migration review.

## GitHub Release Body

Use this document as the release body for tag `v2.3.0` after hosted CI and the
publication checklist succeed.
