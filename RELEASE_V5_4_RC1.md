# manga-director v5.4.0 RC1

Release date: 2026-08-03  
Canonical package version: `5.4.0rc1`  
Frontend version: `5.4.0-rc.1`

## Creative Quality Framework

v5.4.0 RC1 completes the optional Creative Quality Framework as a local,
human-gated diagnostic layer. Quality Engine, Review Pipeline, Validation
Engine, Quality Metrics, Release Criteria, Intelligence, Governance, Audit,
Reliability, Lifecycle, and SDK reports are additive and non-operational.

No automatic review, validation execution, CI/CD control, workflow mutation,
policy enforcement, approval, recovery, signing, publishing, or release action
is introduced.

## Compatibility

v5.4.0 RC1 is backward-compatible with v5.0 LTS and v5.3. Existing Python API,
CLI, FastAPI/REST, MCP, Web UI, Repository, Workflow, Extension SDK, Provider,
and Backend contracts remain valid. Quality Framework adoption is optional and
requires no data or configuration migration.

The StateMachine remains authoritative: every workflow execution creates exactly
one Page, stages cannot be skipped, image generation needs a persisted
storyboard, and Page approval needs a completed quality review.

## RC evidence

- [Architecture summary](docs/ARCHITECTURE_SUMMARY_V5_4_RC1.md)
- [Compatibility verification](docs/COMPATIBILITY_V5_4_RC1.md)
- [Benchmark verification](docs/BENCHMARK_V5_4_RC1.md)
- [Security audit](docs/SECURITY_AUDIT_V5_4_RC1.md)
- [Package audit](docs/PACKAGE_AUDIT_V5_4_RC1.md)
- [Release checklist](docs/RELEASE_CHECKLIST_V5_4_RC1.md)
- [RC readiness report](docs/V5_4_RC1_READINESS_REPORT.md)
- [GitHub release notes](docs/GITHUB_RELEASE_V5_4_RC1.md)

## Publication boundary

The RC is locally ready for maintainer review. Protected CI, external
vulnerability lookup, signing, tag creation, GitHub pre-release publication,
PyPI upload, hosted scanning, and downstream feedback remain maintainer gates.
