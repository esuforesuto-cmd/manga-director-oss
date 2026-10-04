# manga-director v5.2.0

Release date: 2026-08-03  
Canonical package and frontend version: `5.2.0`

## Creative Automation Framework

v5.2.0 completes the Creative Automation Framework as an additive, local-first,
human-gated diagnostic layer. Automation Engine, Rule Engine, Event Bus,
Workflow Templates, Automation Registry, Intelligence, Governance,
Observability, Reliability, Lifecycle, and Unified SDK Automation reports are
available without changing existing service ownership.

No automation execution, event delivery, queue, scheduling, workflow mutation,
policy enforcement, telemetry, lifecycle transition, recovery, self-learning,
or automatic approval is introduced.

## Compatibility

v5.2.0 preserves v5.0 LTS and v5.1 Python API, CLI, FastAPI/REST, MCP, Web
UI, Repository, Workflow, Extension SDK, Provider, and Backend contracts.
Automation is optional and no data migration is required.

The StateMachine remains authoritative: each workflow execution creates exactly
one Page, stages cannot be skipped, image generation needs a persisted
storyboard, and approval needs a completed quality review.

## Release evidence

- [Architecture summary](docs/ARCHITECTURE_SUMMARY_V5_2.md)
- [Compatibility verification](docs/COMPATIBILITY_V5_2.md)
- [Workflow regression](docs/WORKFLOW_REGRESSION_V5_2.md)
- [Benchmark verification](docs/BENCHMARK_V5_2.md)
- [Security audit](docs/SECURITY_AUDIT_V5_2.md)
- [Package audit](docs/PACKAGE_AUDIT_V5_2.md)
- [Release checklist](docs/RELEASE_CHECKLIST_V5_2.md)
- [Release-ready report](docs/V5_2_RELEASE_READY_REPORT.md)
- [Automation completion summary](docs/V5_2_AUTOMATION_SUMMARY.md)
- [Migration guide](docs/MIGRATION_V5_1_TO_V5_2.md)

## Publication boundary

Local final assets are ready for maintainer publication after externally
controlled dependency scanning, protected CI, signing, GitHub release, and
PyPI publication gates pass.
