# manga-director v4.5.0 RC1

Release candidate date: 2026-08-02  
Canonical package version: `4.5.0rc1`  
Frontend package version: `4.5.0-rc.1`

## Scope

v4.5 RC1 integrates the additive Creative Intelligence Ecosystem work reviewed
through Iterations 1--3:

- Creative Service Registry, Service Intelligence, and Service Trust Framework
- Plugin Foundation, Plugin Analytics, and Plugin Governance
- Workflow Marketplace Foundation and Workflow Insights
- Knowledge Exchange, Federation Registry, analytics, and governance
- Ecosystem Dashboard, Governance, and Reliability projections

These modules provide immutable, caller-supplied analysis and review DTOs. They
do not register or invoke services, load or execute plugins, operate a
marketplace, synchronize knowledge, establish federation networking, enforce a
policy, monitor a runtime, or perform recovery.

## Compatibility

v4.5 RC1 is additive and retains v4.4 compatibility for the Python API, CLI,
FastAPI and REST API, MCP, Repository, Workflow, Plugin, Extension SDK,
Provider, Backend, and Web UI. The domain StateMachine remains the sole source
of truth for workflow transitions.

The mandatory workflow rules remain unchanged: one page per execution, no stage
skipping, persisted storyboard before image generation, completed quality review
before approval, and no multi-page generation request.

No migration is required from v4.4.

## RC evidence

- [Architecture summary](docs/ARCHITECTURE_SUMMARY_V4_5_RC1.md)
- [Compatibility verification](docs/COMPATIBILITY_V4_5_RC1.md)
- [Workflow regression verification](docs/WORKFLOW_REGRESSION_V4_5_RC1.md)
- [Benchmark verification](docs/BENCHMARK_V4_5_RC1.md)
- [Security audit](docs/SECURITY_AUDIT_V4_5_RC1.md)
- [Package audit](docs/PACKAGE_AUDIT_V4_5_RC1.md)
- [Release checklist](docs/RELEASE_CHECKLIST_V4_5_RC1.md)
- [Ecosystem RC1 readiness report](docs/V4_5_RC1_READINESS_REPORT.md)

## Publication boundary

This repository contains the reviewed RC assets. Protected CI, tag signing,
GitHub release publication, and PyPI upload remain maintainer-controlled steps.
