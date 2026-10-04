# manga-director v2.1.0

## What's New

v2.1.0 is the stable, backward-compatible promotion of the reviewed v2.1.0
release candidate. It adds no workflow, provider, database, plugin, or UI
feature beyond the RC scope.

## Quality Improvements

- Release contracts protect package, MCP, frontend-version, typed-marker, SBOM,
  documentation-link, and public-entry-point expectations.
- Architecture, dependency-direction, persistence, workflow-resume, batch,
  Plugin, Extension SDK, MCP, security, and package-install regression checks
  are part of the maintained test suite.

## Performance Improvements

Provider-free Workflow, Repository, SQLite, Prompt, LLM, Image, Notification,
and Batch smoke measurements show no regression relative to the retained v2.0
baseline artifact. This is a local regression signal, not a throughput claim.

## DX Improvements

Make/Task commands, setup and verification scripts, cached CI jobs, Python and
frontend quality gates, package validation, and governance documents support
contributors and maintainers.

## Compatibility

v1.x and v2.0 contracts remain supported for shipped surfaces: root Python API,
CLI, forward-only Page workflow, Project persistence, Repository, local MCP,
Plugin, and Extension SDK. No data migration is required from v2.0.

## Migration

See [Migration Guide](docs/MIGRATION_v1_to_v2.md). Install optional database
support with `manga-director[postgresql,migrations]` only when required.

## Known Limitations

FastAPI/OpenAPI and Automation runtimes are not included in this source
baseline. The Web UI is a tested presentation scaffold that expects a separately
compatible HTTP service. Real network provider calls, distributed workers,
parallel page execution, remote extension installation, and a marketplace are
outside this release.

## Roadmap v2.2

The v2.2 planning scope remains governed by [ROADMAP_v2_1](docs/ROADMAP_v2_1.md)
and [ROADMAP_v2](docs/ROADMAP_v2.md). It is planning only; no v2.2 feature is
part of this release.

## GitHub Release Body

Use this document as the body for the `v2.1.0` GitHub Release after hosted CI
has passed and the release checklist has been signed off.
