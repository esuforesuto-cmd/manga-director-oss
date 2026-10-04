# manga-director v5.2.0 RC1

Release date: 2026-08-03  
Canonical package version: `5.2.0rc1`  
Frontend version: `5.2.0-rc.1`

## Creative Automation Framework

v5.2.0 RC1 completes the optional Creative Automation Framework as a local,
human-gated diagnostic layer. Automation Engine, Rule Engine, Event Bus,
Workflow Templates, Automation Registry, Intelligence, Governance,
Observability, Reliability, Lifecycle, and SDK maturity reports remain
declarative and non-executing.

No automation execution, event delivery, queue, handler, scheduling, workflow
mutation, policy enforcement, monitoring, recovery, self-learning, or automatic
approval is introduced.

## Compatibility

v5.2.0 RC1 is fully backward-compatible with v5.0 LTS and v5.1. Existing
Python API, CLI, FastAPI/REST, MCP, Web UI, Repository, Workflow, Extension
SDK, Provider, and Backend contracts remain valid. Automation is optional; no
data migration or framework adoption is required.

The StateMachine remains authoritative: each execution creates exactly one
Page, stages cannot be skipped, image generation needs a persisted storyboard,
and approval needs a completed quality review.

## RC evidence

- [Architecture summary](docs/ARCHITECTURE_SUMMARY_V5_2_RC1.md)
- [Compatibility verification](docs/COMPATIBILITY_V5_2_RC1.md)
- [Workflow regression](docs/WORKFLOW_REGRESSION_V5_2_RC1.md)
- [Benchmark verification](docs/BENCHMARK_V5_2_RC1.md)
- [Security audit](docs/SECURITY_AUDIT_V5_2_RC1.md)
- [Package audit](docs/PACKAGE_AUDIT_V5_2_RC1.md)
- [Release checklist](docs/RELEASE_CHECKLIST_V5_2_RC1.md)
- [RC readiness report](docs/V5_2_RC1_READINESS_REPORT.md)
- [GitHub release notes](docs/GITHUB_RELEASE_V5_2_RC1.md)

## Publication boundary

The RC is locally ready for maintainer review. External dependency vulnerability
lookup, protected CI, signing, tag creation, GitHub pre-release publication,
PyPI upload, hosted scanning, and downstream feedback remain controlled by
maintainers.
