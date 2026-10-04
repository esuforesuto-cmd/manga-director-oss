# manga-director v5.4.0

Release date: 2026-08-03  
Canonical package and frontend version: `5.4.0`

## Creative Quality Framework

v5.4.0 completes the optional Creative Quality Framework as a local,
human-gated diagnostic layer. Quality Engine, Review Pipeline, Validation
Engine, Quality Metrics, Release Criteria, Intelligence, Governance, Audit,
Reliability, Lifecycle, and SDK reports remain additive and non-operational.

No automatic review, validation execution, CI/CD control, workflow mutation,
policy enforcement, approval, recovery, signing, publishing, or release action
is introduced.

## Compatibility

v5.4.0 preserves v5.0 LTS and v5.3 Python API, CLI, FastAPI/REST, MCP, Web UI,
Repository, Workflow, Extension SDK, Provider, and Backend contracts. Quality
Framework adoption is optional and requires no data or configuration migration.

The StateMachine remains authoritative: every workflow execution creates exactly
one Page, stages cannot be skipped, image generation needs a persisted
storyboard, and Page approval needs a completed quality review.

## Release evidence

- [Architecture summary](docs/ARCHITECTURE_SUMMARY_V5_4.md)
- [Creative Quality Framework completion report](docs/V5_4_CREATIVE_QUALITY_FRAMEWORK_COMPLETION_REPORT.md)
- [Migration guide](docs/MIGRATION_V5_3_TO_V5_4.md)
- [Compatibility verification](docs/COMPATIBILITY_V5_4.md)
- [Benchmark verification](docs/BENCHMARK_V5_4.md)
- [Security audit](docs/SECURITY_AUDIT_V5_4.md)
- [Package audit](docs/PACKAGE_AUDIT_V5_4.md)
- [Release checklist](docs/RELEASE_CHECKLIST_V5_4.md)
- [Release-ready report](docs/V5_4_RELEASE_READY_REPORT.md)
- [GitHub release notes](docs/GITHUB_RELEASE_V5_4.md)

## Publication boundary

This repository contains the final release artifacts and local validation
evidence. Signing, tag creation, GitHub publication, PyPI upload, protected CI,
and any external vulnerability scan remain authorized maintainer actions.
