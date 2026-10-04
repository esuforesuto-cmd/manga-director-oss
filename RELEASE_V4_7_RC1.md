# manga-director v4.7.0 RC1

Release candidate date: 2026-08-02  
Canonical package version: `4.7.0rc1`  
Frontend package version: `4.7.0-rc.1`

## Scope

v4.7 RC1 integrates the additive Creative Decision Platform reviewed through
Iterations 1--3: Decision Engine, Recommendation Framework, Review
Intelligence, Approval Platform, Executive Dashboard, Governance, and
Reliability.

The modules create immutable, caller-supplied report DTOs. They do not collect
or persist evidence, enforce policy, select a decision or recommendation,
complete a review, grant an approval, change workflow state, execute work,
monitor, retry, recover, or call an external service.

## Compatibility

v4.7 RC1 is additive and retains v4.6 compatibility for the Python API, CLI,
FastAPI and REST API, MCP, Repository, Workflow, Agent Platform, Plugin,
Extension SDK, Provider, Backend, and Web UI. The domain StateMachine remains
the sole source of truth for workflow transitions.

The mandatory workflow rules remain unchanged: one page per execution, no
stage skipping, persisted storyboard before image generation, completed quality
review before approval, and no multi-page generation request.

No migration is required from v4.6.

## RC evidence

- [Architecture summary](docs/ARCHITECTURE_SUMMARY_V4_7_RC1.md)
- [Compatibility verification](docs/COMPATIBILITY_V4_7_RC1.md)
- [Workflow regression verification](docs/WORKFLOW_REGRESSION_V4_7_RC1.md)
- [Benchmark verification](docs/BENCHMARK_V4_7_RC1.md)
- [Security audit](docs/SECURITY_AUDIT_V4_7_RC1.md)
- [Package audit](docs/PACKAGE_AUDIT_V4_7_RC1.md)
- [Release checklist](docs/RELEASE_CHECKLIST_V4_7_RC1.md)
- [Decision Platform RC1 readiness report](docs/V4_7_RC1_READINESS_REPORT.md)

## Publication boundary

This repository contains the reviewed RC assets. Protected CI, tag signing,
GitHub pre-release publication, and PyPI upload remain maintainer-controlled
steps.
