# manga-director v4.6.0 RC1

Release candidate date: 2026-08-02  
Canonical package version: `4.6.0rc1`  
Frontend package version: `4.6.0-rc.1`

## Scope

v4.6 RC1 integrates the additive Creative Intelligence OS work reviewed through
Iterations 1--3:

- Unified Creative Context and Cross-Agent Memory reference reports
- Creative Reasoning and Adaptive Workflow analysis reports
- Intelligence Hub composition and dashboard reports
- Intelligence Governance, Context Governance, Reasoning Audit, Workflow
  Observability, and Intelligence Reliability reports

These modules provide immutable, caller-supplied analysis and review DTOs. They
do not collect or persist context, read/write/synchronize memory, update a
model, invoke agents, make autonomous decisions, mutate or execute workflows,
monitor a runtime, alert, retry, recover, or call an external service.

## Compatibility

v4.6 RC1 is additive and retains v4.5 compatibility for the Python API, CLI,
FastAPI and REST API, MCP, Repository, Workflow, Agent Platform, Plugin,
Extension SDK, Provider, Backend, and Web UI. The domain StateMachine remains
the sole source of truth for workflow transitions.

The mandatory workflow rules remain unchanged: one page per execution, no stage
skipping, persisted storyboard before image generation, completed quality review
before approval, and no multi-page generation request.

No migration is required from v4.5.

## RC evidence

- [Architecture summary](docs/ARCHITECTURE_SUMMARY_V4_6_RC1.md)
- [Compatibility verification](docs/COMPATIBILITY_V4_6_RC1.md)
- [Workflow regression verification](docs/WORKFLOW_REGRESSION_V4_6_RC1.md)
- [Benchmark verification](docs/BENCHMARK_V4_6_RC1.md)
- [Security audit](docs/SECURITY_AUDIT_V4_6_RC1.md)
- [Package audit](docs/PACKAGE_AUDIT_V4_6_RC1.md)
- [Release checklist](docs/RELEASE_CHECKLIST_V4_6_RC1.md)
- [Creative Intelligence RC1 readiness report](docs/V4_6_RC1_READINESS_REPORT.md)

## Publication boundary

This repository contains the reviewed RC assets. Protected CI, tag signing,
GitHub pre-release publication, and PyPI upload remain maintainer-controlled
steps.
