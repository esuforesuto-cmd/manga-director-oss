# manga-director v5.7.0 RC1

Release date: 2026-08-09  
Canonical package version: `5.7.0rc1`  
Frontend version: `5.7.0-rc.1`

## Manga Production Platform

v5.7.0 RC1 composes the existing one-page Production Pipeline, Workspace,
Project, Asset, Automation, and Plugin reports into an optional, read-only
Production Platform diagnostic. It standardizes supplied evidence for project
coordination without dispatching work or changing any production state.

The RC does not generate images, execute automation, schedule tasks, restore
snapshots, change Plugin lifecycle, publish events, approve pages, export
content, mutate the workflow, or access repositories.

## Compatibility

Existing Python API, CLI, FastAPI/REST, MCP, Web UI, Repository, SDK, Plugin,
and StateMachine contracts remain unchanged. The StateMachine remains
authoritative: exactly one page per execution, no skipped stage, persisted
storyboard before image generation, and completed quality review before
approval.

## RC evidence

- [RC1 report](docs/V5_7_RC1_REPORT.md)
- [Platform integration](docs/PLATFORM_INTEGRATION_REPORT.md)
- [Workspace compatibility](docs/WORKSPACE_COMPATIBILITY_REPORT.md)
- [Automation verification](docs/AUTOMATION_REPORT.md)
- [Quality gate](docs/QUALITY_GATE_REPORT.md)
- [Release checklist](docs/RELEASE_CHECKLIST.md)
- [Known issues](docs/KNOWN_ISSUES.md)

## Publication boundary

This package is prepared for local RC review. Protected CI, external CVE
lookup, signing, tag creation, GitHub pre-release publication, and PyPI upload
remain maintainer-controlled actions.
