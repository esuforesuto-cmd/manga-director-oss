# manga-director v5.1.0

Release date: 2026-08-03  
Canonical package and frontend version: `5.1.0`

## Composable Creative Platform

v5.1.0 completes the Composable Creative Platform as an additive, local-first,
human-governed composition layer. Capability Registry, Feature Packs, Platform
Profiles, Solution Templates, Composition Engine, Governance, Observability,
Module Lifecycle, Reliability, and Unified SDK maturity previews are available
without changing existing service ownership.

No module loading, extension installation, runtime routing, service invocation,
policy enforcement, telemetry, lifecycle transition, recovery, workflow
execution, or automatic approval is introduced.

## Compatibility

v5.1.0 preserves v5.0 LTS Python API, CLI, FastAPI/REST, MCP, Web UI,
Repository, Workflow, Extension SDK, Provider, and Backend contracts.
Composition is optional and no data migration is required.

The StateMachine remains authoritative: each workflow execution creates exactly
one Page, stages cannot be skipped, image generation needs a persisted
storyboard, and approval needs a completed quality review.

## Release evidence

- [Architecture summary](docs/ARCHITECTURE_SUMMARY_V5_1.md)
- [Compatibility verification](docs/COMPATIBILITY_V5_1.md)
- [Workflow regression](docs/WORKFLOW_REGRESSION_V5_1.md)
- [Benchmark verification](docs/BENCHMARK_V5_1.md)
- [Security audit](docs/SECURITY_AUDIT_V5_1.md)
- [Package audit](docs/PACKAGE_AUDIT_V5_1.md)
- [Release checklist](docs/RELEASE_CHECKLIST_V5_1.md)
- [Release-ready report](docs/V5_1_RELEASE_READY_REPORT.md)
- [Platform completion summary](docs/V5_1_PLATFORM_SUMMARY.md)
- [Migration guide](docs/MIGRATION_V5_0_TO_V5_1.md)

## Publication boundary

Local final assets are ready for maintainer publication after externally
controlled dependency scanning, protected CI, signing, GitHub release, and
PyPI publication gates pass.
