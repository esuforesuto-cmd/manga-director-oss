# manga-director v5.1.0 RC1

Release date: 2026-08-03  
Canonical package version: `5.1.0rc1`  
Frontend version: `5.1.0-rc.1`

## Composable Creative Platform

v5.1.0 RC1 completes the Composable Creative Platform as an additive,
local-first metadata composition layer. Capability Registry, Feature Packs,
Platform Profiles, Solution Templates, Composition Engine, Governance,
Observability, Module Lifecycle, Reliability, and SDK maturity previews are
declarative and human-governed.

No module loading, extension installation, runtime routing, service invocation,
policy enforcement, telemetry, lifecycle transition, recovery, workflow
execution, or automatic approval is introduced.

## Compatibility

v5.1.0 RC1 is fully backward-compatible with v5.0 LTS. Existing Python API,
CLI, FastAPI/REST, MCP, Web UI, Repository, Workflow, Extension SDK, Provider,
and Backend contracts remain valid. Composition is optional; no data migration
or profile adoption is required.

The StateMachine remains authoritative: each execution creates exactly one
Page, stages cannot be skipped, image generation needs a persisted storyboard,
and approval needs a completed quality review.

## RC evidence

- [Architecture summary](docs/ARCHITECTURE_SUMMARY_V5_1_RC1.md)
- [Compatibility verification](docs/COMPATIBILITY_V5_1_RC1.md)
- [Workflow regression](docs/WORKFLOW_REGRESSION_V5_1_RC1.md)
- [Benchmark verification](docs/BENCHMARK_V5_1_RC1.md)
- [Security audit](docs/SECURITY_AUDIT_V5_1_RC1.md)
- [Package audit](docs/PACKAGE_AUDIT_V5_1_RC1.md)
- [Release checklist](docs/RELEASE_CHECKLIST_V5_1_RC1.md)
- [RC readiness report](docs/V5_1_RC1_READINESS_REPORT.md)
- [GitHub release notes](docs/GITHUB_RELEASE_V5_1_RC1.md)

## Publication boundary

The RC is locally ready for maintainer review. External dependency vulnerability
lookup, protected CI, signing, tag creation, GitHub pre-release publication,
PyPI upload, hosted scanning, and downstream feedback remain controlled by
maintainers.
