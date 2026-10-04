# GitHub Release Notes — v6.0.0

## Creative Production Platform stable

v6.0 stabilizes the optional, read-only Creative Production Platform: Platform
Foundation, Knowledge and Context Intelligence, Workflow and Automation
projections, Collaboration, Platform Kernel, SDK, Extension, Marketplace,
Policy, Governance, and Observability.

## Compatibility

v6.0 preserves v5.x Python API, CLI, FastAPI/REST, MCP, Web UI, Repository,
Workflow, SDK, Plugin, and StateMachine contracts. No migration is required;
see the [migration guide](MIGRATION_V6_0.md).

## Before publishing

Run protected CI, external CVE review, artifact signing, tag creation, and
PyPI upload under maintainer authority. Marketplace publication remains an
explicit deployment-owned operation.
