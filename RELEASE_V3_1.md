# manga-director v3.1.0

## What's New

v3.1.0 promotes reviewed RC1 evidence without expanding scope. It includes
additive, diagnostic-only Creative Collaboration, Knowledge Evolution,
Operations Platform, Developer Productivity, Creative Review, Knowledge
Analytics, Operations Intelligence, Creative Governance, Knowledge Reliability,
Operational Readiness, and Release Quality DTOs.

## Creative Collaboration

Workspace, member, session, review-assignment, approval-state, and activity
DTOs make human collaboration visible. They do not edit a Project, dispatch an
Agent, advance a Page, or grant approval.

## Knowledge Evolution

Version, snapshot, diff, timeline, analytics, reliability, and governance
reports are read-only Repository-port projections. They preserve redaction and
do not create a mutable Knowledge store.

## Operations Platform

Project, workflow, quality, and release metrics plus operational health are
transport-neutral DTOs. They do not deploy, configure, or publish.

## Developer Productivity

Workspace diagnostics, template recommendations, and DX reports are
non-executing development aids. CLI, optional FastAPI, MCP, and Web UI render
shared results without duplicating Domain rules.

## Production and Performance Improvements

Production runtime, observability, diagnostics, reporting, recovery,
repository-integrity, and configuration-validation evidence remain advisory.
Provider-free benchmark smoke covers bounded collaboration, Knowledge,
operations, workflow, diagnostics, reporting, health, and developer paths.

## Compatibility and Migration

v3.1.0 is backward compatible with v1.x, v2.0.x-v2.7.x, and v3.0.x public
contracts. No workflow, Project, configuration, repository, database, Plugin,
Extension SDK, Provider, or Image Backend migration is required. See
[Migration](docs/MIGRATION_V3_1.md) and
[Compatibility](docs/COMPATIBILITY_V3_1.md).

## Known Limitations

Live Providers, automatic Agent execution, automatic review or approval, Cloud
services, marketplace, and distributed runtime remain out of scope. All v3.1
services are advisory and cannot bypass the StateMachine.

## Roadmap v3.2

Future work must remain opt-in and preserve one-Page StateMachine authority.

## GitHub Release Body

Use this document as the GitHub Release body for tag `v3.1.0` after hosted CI,
dependency/CVE audit, secret scan, and publication checks pass.
