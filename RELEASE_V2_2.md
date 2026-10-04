# manga-director v2.2.0

## What's New

v2.2.0 promotes the reviewed v2.2.0 RC1 to the stable release line. It adds no
new workflow behavior during promotion: the release formalizes the v2.2
large-project, reliability, diagnostics, and runtime-quality work behind the
existing public contracts.

## Performance Improvements

- Selective repository reads, metadata indexes, incremental persistence, and
  database query improvements remain behind the existing Repository ports.
- Batch checkpoints, progress snapshots, execution statistics, and retry
  summaries retain sequential execution by default.
- Plugin, Extension SDK, configuration, and EventBus cache paths have
  provider-free benchmark and repeatability coverage.

## Reliability Improvements

- Workflow recovery preserves forward-only StateMachine validation.
- Repository integrity and recovery helpers validate persisted Project
  snapshots without coupling Core to a concrete adapter.
- Health and diagnostics expose safe DTO, JSON, and Markdown representations.
- Plugin and Extension loader failures stay isolated and surface as typed
  errors.

## Developer Experience

The release retains unified local quality commands, typed public exports,
release-contract tests, backend/frontend/package/security/nightly CI lanes,
and reproducible provider-free benchmark smoke checks.

## Compatibility

v1.x, v2.0.x, and v2.1.x public Python imports, CLI commands, local MCP
protocol, Repository interface, page workflow, Plugin API, and Extension SDK
remain compatible. See [the compatibility audit](docs/COMPATIBILITY_V2_2.md).

## Migration

No migration is required from v1.x, v2.0.x, or v2.1.x for the shipped public
surfaces. Existing file-backed projects remain supported. Review
[the migration guide](docs/MIGRATION_v1_to_v2.md) before choosing optional
database or delivery adapters.

## Known Limitations

- OpenAI and ComfyUI image adapters and non-mock LLM providers are intentional
  API-boundary stubs and make no provider network calls.
- FastAPI/OpenAPI and Automation runtimes are not shipped in this source
  baseline. The Web UI is independently built and requires a compatible
  external HTTP service.
- Parallel/distributed workflow execution, remote plugin delivery, and cloud
  monitoring are not included.

## Roadmap v2.3

v2.3 planning will remain issue-driven and preserve the Core architecture.
Candidates include controlled performance baselines, provider integration work
when separately approved, and separately reviewed delivery runtimes; none is
part of this release.

## GitHub Release Body

Use this document as the body for the `v2.2.0` GitHub Release after the hosted
CI workflows for the signed or approved `v2.2.0` tag are green.
