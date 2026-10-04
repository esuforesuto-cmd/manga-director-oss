# manga-director v6.0.0rc1

Release candidate date: 2026-08-09  
Python package version: `6.0.0rc1`  
Web package version: `6.0.0-rc.1`

## Creative Production Platform

RC1 integrates optional, read-only v6.0 Platform Foundation, Intelligence,
and Platform Kernel reports for Knowledge, Context, Workflow, Automation,
Collaboration, SDK, Extension, Marketplace, Policy, Governance, and
Observability.

The release introduces no runtime execution, automatic approval, workflow
mutation, repository mutation, Extension loading, Marketplace publication,
policy enforcement, telemetry emission, or external connectivity.

## Compatibility

All v5.x Python API, CLI, FastAPI/REST, MCP, Web UI, Repository, Workflow,
SDK, Plugin, and StateMachine contracts remain available. v5.7.0 is the
stable compatibility baseline; v6 services are opt-in and use exactly one
caller-supplied Page context.

## Release evidence

- [RC1 report](docs/V6_0_RC1_REPORT.md)
- [Platform integration](docs/PLATFORM_INTEGRATION_REPORT.md)
- [SDK compatibility](docs/SDK_COMPATIBILITY_REPORT.md)
- [Extension compatibility](docs/EXTENSION_COMPATIBILITY_REPORT.md)
- [Governance](docs/GOVERNANCE_REPORT.md)
- [Observability](docs/OBSERVABILITY_REPORT.md)
- [Quality gate](docs/QUALITY_GATE_REPORT.md)
- [Release checklist](docs/RELEASE_CHECKLIST.md)
- [Known issues](docs/KNOWN_ISSUES.md)
- [Migration guide](docs/MIGRATION_V5_7_TO_V6_0.md)
