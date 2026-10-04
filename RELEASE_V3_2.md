# manga-director v3.2.0

## What's New

v3.2.0 promotes the reviewed RC1 scope to a stable release without expanding
it. The release adds only optional, typed, read-only application projections;
the Core Domain, StateMachine, Repository interface, and workflow behavior are
unchanged.

## Creative Studio

Creative Studio provides workspace, creative-session, layout, dashboard,
activity, insight, reliability, and readiness DTOs for human planning and
review. It never writes a Project, dispatches an Agent, advances a Page, or
grants approval.

## Asset Intelligence

Asset Intelligence projects catalog, metadata, category, relationship, usage,
quality, governance, lifecycle, integrity, and risk evidence through the
existing Repository boundary. It does not add a mutable asset store, remote
lookup, or external model call.

## Workflow Profiles

Workflow Profiles describe the existing Page StateMachine, pipeline stages,
execution context, efficiency, timeline, bottleneck, health, and
recommendations. They present the sole legal next command and never transition
or rewrite a workflow.

## Production Analytics

Production Analytics provides project, workflow, review, quality, insight,
trend, operational intelligence, and release-readiness reports. These reports
are diagnostic only: they do not deploy, publish, configure, or automate work.

## Production Improvements

Production runtime, observability, diagnostics, reporting, recovery,
repository integrity, health, and configuration validation remain
transport-neutral advisory evidence.

## Performance Improvements

Provider-free benchmark smoke covers the bounded v3.2 DTO paths and detects
obvious local regressions without promising machine-independent timing.

## Developer Experience

CLI, optional FastAPI, MCP, and Web UI delivery paths render shared typed DTOs.
The package keeps a single canonical version source, includes typing metadata,
and publishes SBOM and dependency license review assets.

## Compatibility and Migration Guide

v3.2.0 is backward compatible with v1.x, v2.0.x-v2.7.x, v3.0.x, and v3.1.x
public contracts. No workflow, Project, configuration, repository, database,
Plugin, Extension SDK, Provider, or Image Backend migration is required. See
[Migration](docs/MIGRATION_V3_2.md) and
[Compatibility](docs/COMPATIBILITY_V3_2.md).

## Known Limitations

Live Provider selection, autonomous AI, automatic Agent execution, automatic
review or approval, Cloud services, marketplace, and distributed runtime remain
out of scope. The v3.2 reports cannot bypass StateMachine authority.

## Roadmap v3.3

Future v3.3 planning should remain opt-in, preserve one-Page workflow
authority, and require compatibility, security, and production-readiness
evidence before implementation.

## GitHub Release Body

Use this document as the GitHub Release body for tag `v3.2.0` after the hosted
tagged CI, dependency/CVE audit, secret scan, and publication checks pass.
