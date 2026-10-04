# manga-director v4.4.0 RC1

Released candidate: 2026-08-02  
Canonical version: `4.4.0rc1` (`4.4.0-rc.1` in frontend metadata)

## Scope

This release candidate integrates the additive v4.4 Enterprise Creative Platform:
Enterprise Workspace, Team Collaboration, Portfolio Management, Extension
Registry, Marketplace Catalog, Governance, and Reliability. It adds no
enterprise runtime, remote marketplace, extension execution, Cloud capability,
payment/billing, workflow automation, or public API replacement.

## Compatibility

v4.3 remains fully backward compatible across the Python API, CLI, FastAPI and
REST API, MCP, Repository, Workflow, Plugin, Provider, Backend, Web UI, and
Extension SDK. The domain StateMachine remains the transition authority.

The existing workflow safety invariants remain unchanged: exactly one Page per
execution, no skipped stage, persisted storyboard before image generation, and
completed quality review before approval.

## RC validation record

- [Architecture summary](docs/ARCHITECTURE_SUMMARY_V4_4_RC1.md)
- [Compatibility verification](docs/COMPATIBILITY_V4_4_RC1.md)
- [Workflow regression verification](docs/WORKFLOW_REGRESSION_V4_4_RC1.md)
- [Benchmark verification](docs/BENCHMARK_V4_4_RC1.md)
- [Security audit](docs/SECURITY_AUDIT_V4_4_RC1.md)
- [Package audit](docs/PACKAGE_AUDIT_V4_4_RC1.md)
- [Release checklist](docs/RELEASE_CHECKLIST_V4_4_RC1.md)
- [Enterprise RC1 readiness report](docs/V4_4_RC1_READINESS_REPORT.md)

## Upgrade guidance

No migration is required from v4.3. Existing callers keep their contracts;
v4.4 DTO projections are opt-in and advisory. Maintainers should run the
published release checklist before tagging or publishing the candidate.
