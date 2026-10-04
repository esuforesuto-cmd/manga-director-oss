# GitHub Release Notes — v5.7.0

## Manga Production Platform stable

v5.7.0 stabilizes the optional Production Platform: Workspace, Project, Asset,
Automation, Plugin, Production Orchestrator, Event, Scheduler, Snapshot, and
Analytics reports for one existing page.

Platform API v1, Plugin API v1, and Workspace Standard v1 are frozen. The
release is additive and read-only: it does not execute automation, mutate a
workflow, change Plugin lifecycle, or create creative or publishing output.

## Compatibility

v5.7.0 preserves v5.x Python API, CLI, FastAPI/REST, MCP, Web UI, Repository,
Workflow, SDK, Plugin, and StateMachine compatibility. No data migration is
required; see the [migration guide](MIGRATION_V5_7.md).

## Before publishing

Run protected CI, external CVE review, artifact signing, the clean-environment
package installation check, tag creation, and PyPI upload under maintainer
authority.
