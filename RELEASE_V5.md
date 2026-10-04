# manga-director v5.0.0

Release date: 2026-08-03  
Canonical package and frontend version: `5.0.0`

## One Creative Platform

v5.0.0 completes One Creative Platform as an additive, local-first composition
layer. Unified Platform, Context, API Surface, Runtime, SDK, Governance,
Observability, Reliability, Lifecycle, Developer Experience, and Maturity
reports give users a consistent view of v2-v4 capabilities without transferring
their ownership.

No execution behavior is introduced. The platform does not route or invoke
services, replace Runtime entry points, collect telemetry, monitor, alert,
recover, persist shared data, enforce policy, execute workflows, or call
external services.

## Compatibility

v5.0.0 is additive over v4.8. Python API, CLI, FastAPI/REST, MCP, Web UI,
Repository, Workflow, Plugin, Extension SDK, Provider, and Backend contracts
remain supported. No data migration is required.

StateMachine remains the workflow authority. Each execution processes exactly
one Page; stages cannot be skipped; image generation needs a persisted
storyboard; approval needs a completed quality review; and multi-page requests
remain invalid.

## Release evidence

- [Architecture summary](docs/ARCHITECTURE_SUMMARY_V5.md)
- [Compatibility verification](docs/COMPATIBILITY_V5.md)
- [Workflow regression](docs/WORKFLOW_REGRESSION_V5.md)
- [Benchmark verification](docs/BENCHMARK_V5.md)
- [Security audit](docs/SECURITY_AUDIT_V5.md)
- [Package audit](docs/PACKAGE_AUDIT_V5.md)
- [Release checklist](docs/RELEASE_CHECKLIST_V5.md)
- [Release-ready report](docs/V5_RELEASE_READY_REPORT.md)
- [LTS readiness report](docs/V5_LTS_READINESS_REPORT.md)
- [Platform completion summary](docs/V5_PLATFORM_SUMMARY.md)
- [Migration guide](docs/MIGRATION_V4_TO_V5.md)

## Publication boundary

The local final release assets and package are ready for maintainer publication
after outstanding externally controlled security, protected-CI, signing, and
publication checks pass.

