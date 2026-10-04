# manga-director v5.6.0 RC1

Release date: 2026-08-09  
Canonical package version: `5.6.0rc1`  
Frontend version: `5.6.0-rc.1`

## Manga Production OS

v5.6.0 RC1 adds an optional Manga Production OS layer for exactly one existing
page. The Story, Character, Page, Review, and Export Engines are additive,
transport-neutral reports that reuse supplied workflow evidence.

They do not generate an image, rewrite story content, approve a page, mutate a
workflow, create an export, publish content, or access a repository.

## Compatibility

Existing Python API, CLI, FastAPI/REST, MCP, Web UI, Repository, SDK, and
StateMachine contracts remain unchanged. The StateMachine remains authoritative:
one page per execution, no skipped stage, a persisted storyboard before image
generation, and a completed quality review before approval.

## RC evidence

- [RC1 report](docs/V5_6_RC1_REPORT.md)
- [Integration report](docs/INTEGRATION_REPORT.md)
- [Compatibility report](docs/COMPATIBILITY_REPORT.md)
- [Performance report](docs/PERFORMANCE_REPORT.md)
- [Quality-gate report](docs/QUALITY_GATE_REPORT.md)
- [Release checklist](docs/RELEASE_CHECKLIST.md)
- [Known issues](docs/KNOWN_ISSUES.md)

## Publication boundary

The package is prepared for local RC review only. Signing, protected CI, tag
creation, GitHub pre-release publication, PyPI upload, and external CVE review
remain maintainer-controlled actions.
