# manga-director v5.0.0 RC1

Release date: 2026-08-03  
Canonical package version: `5.0.0rc1`  
Canonical frontend version: `5.0.0-rc.1`

## One Creative Platform

v5.0.0 RC1 finalizes review of the additive One Creative Platform: Unified
Platform, Context, API Surface, Runtime, SDK, Governance, Observability,
Reliability, Lifecycle, Developer Experience, and Maturity reports. These
capabilities are local, immutable, transport-neutral, human-operated, and
diagnostic.

No new execution behavior is introduced. The RC does not route or invoke
services, replace Runtime entry points, collect telemetry, monitor, alert,
recover, persist shared platform data, enforce policy, execute a workflow, or
call external services.

## Compatibility

v5.0.0 RC1 is additive over v4.8. Existing Python API, CLI, FastAPI/REST, MCP,
Web UI, Repository, Workflow, Plugin, Extension SDK, Provider, and Backend
contracts remain supported. No data migration is required.

StateMachine remains authoritative. Workflow execution is exactly one Page;
stages cannot be skipped; a persisted storyboard is required before image
generation; a completed quality review is required before approval; and
multi-page generation requests remain invalid.

## RC evidence

- [Architecture summary](docs/ARCHITECTURE_SUMMARY_V5_RC1.md)
- [Compatibility review](docs/COMPATIBILITY_V5_RC1.md)
- [Workflow regression](docs/WORKFLOW_REGRESSION_V5_RC1.md)
- [Benchmark report](docs/BENCHMARK_V5_RC1.md)
- [Security audit](docs/SECURITY_AUDIT_V5_RC1.md)
- [Package audit](docs/PACKAGE_AUDIT_V5_RC1.md)
- [Release checklist](docs/RELEASE_CHECKLIST_V5_RC1.md)
- [RC readiness report](docs/V5_RC1_READINESS_REPORT.md)

## Publication boundary

Local RC assets are ready for maintainer review. Protected CI, signing, tag
creation, GitHub pre-release publication, and PyPI upload require maintainer
authority.

