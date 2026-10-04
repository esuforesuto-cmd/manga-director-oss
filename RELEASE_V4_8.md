# manga-director v4.8.0

Release date: 2026-08-02  
Canonical package and frontend version: `4.8.0`

## Creative Operating System

v4.8.0 completes the v4 Creative Operating System through additive Unified
Platform, Modular Runtime, Unified API Surface, Operational Intelligence,
Lifecycle Management, Governance, Observability, and Reliability DTO/report
projections.

These capabilities are local, transport-neutral, and human-operated. They do
not redesign the Core, replace Runtime, route or invoke services, enforce
policy, collect telemetry, monitor, alert, retry, recover, persist evidence,
execute workflows, or call external services.

## Compatibility

v4.8.0 is additive over v4.7. Python API, CLI, FastAPI/REST, MCP, Web UI,
Repository, Workflow, Agent Platform, Plugin, Extension SDK, Provider, and
Backend contracts remain compatible. No migration is required.

StateMachine remains the workflow authority. Exactly one Page is processed per
workflow execution; stages cannot be skipped; a storyboard must be persisted
before image generation; a completed quality review is required before
approval; and multi-page generation requests remain invalid.

## Release evidence

- [Architecture summary](docs/ARCHITECTURE_SUMMARY_V4_8.md)
- [Compatibility verification](docs/COMPATIBILITY_V4_8.md)
- [Workflow regression verification](docs/WORKFLOW_REGRESSION_V4_8.md)
- [Benchmark verification](docs/BENCHMARK_V4_8.md)
- [Security audit](docs/SECURITY_AUDIT_V4_8.md)
- [Package audit](docs/PACKAGE_AUDIT_V4_8.md)
- [Release checklist](docs/RELEASE_CHECKLIST_V4_8.md)
- [Migration guide](docs/MIGRATION_V4_8.md)
- [v4.8 release-ready report](docs/V4_8_RELEASE_READY_REPORT.md)
- [v4 series completion summary](docs/V4_SERIES_SUMMARY.md)

## Publication boundary

The local final release assets are complete. Protected CI, signed tag creation,
GitHub release publication, and PyPI upload require maintainer authority.
