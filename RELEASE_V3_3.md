# manga-director v3.3.0

## What's New

v3.3.0 promotes the reviewed RC1 scope without expanding it. It adds typed,
read-only Application DTO services for Production Pipeline, Quality
Intelligence, Asset Lifecycle, Project Intelligence, and Governance. The Core
Domain, StateMachine, Repository interface, workflow behavior, and public
contracts remain unchanged.

## Production Pipeline

Pipeline stages, transitions, approval evidence, sessions, timelines,
efficiency, bottleneck, and governance reports make the existing workflow
observable. They do not execute, advance, rewrite, or approve a Page.

## Quality Intelligence

Quality metrics, rules, findings, dashboards, trends, review coverage,
consistency, analytics, and governance reports are diagnostic evidence only.
They cannot remediate findings or grant approval.

## Asset Lifecycle

Asset lifecycle, version, history, archive, dependency, usage, consistency,
health, intelligence, and governance projections use the existing Repository
port. They do not add mutable storage, retention, archive, delete, or repair
authority.

## Project Intelligence

Project health, milestones, schedules, resources, risks, delivery forecasts,
operations, and governance reports provide advisory planning evidence. They do
not allocate work, schedule work, or change a Project.

## Governance

Production, Quality, Asset, and Project policy, audit, compliance, retention,
and dashboard DTOs support human review. They never enforce a policy, authorize
a release, or bypass the StateMachine.

## Production and Performance Improvements

Production runtime, observability, diagnostics, reporting, recovery,
repository-integrity, health, and configuration-validation boundaries remain
transport-neutral and advisory. Provider-free benchmark smoke covers the v3.3
projection paths; it detects local regressions without making
machine-independent latency claims.

## Developer Experience

The shared typed DTOs are available through optional CLI, FastAPI, and MCP
delivery seams. Version information remains canonical in
`manga_director._version`; OpenAPI and MCP derive it, while the frontend and
SBOM carry the matching release value.

## Compatibility and Migration Guide

v3.3.0 is backward compatible with documented v1.x, v2.0.x-v2.7.x, v3.0.x,
v3.1.x, and v3.2.x public contracts. No Project, data, configuration,
Repository, workflow, database, Plugin, Extension SDK, Provider, Image Backend,
Automation, or Notification migration is required. See
[Migration](docs/MIGRATION_V3_3.md) and
[Compatibility](docs/COMPATIBILITY_V3_3.md).

## Known Limitations

Autonomous AI, workflow or approval automation, new Providers or Backends,
Cloud services, marketplace, and distributed runtime remain out of scope.
Reports cannot bypass StateMachine authority, create a second workflow, or
generate multiple Pages.

## Roadmap v3.4

The next cycle should be planned openly and remain opt-in, additive, and
evidence-led. Any future work must preserve one-Page workflow authority and
pass compatibility, security, production, and governance validation.

## GitHub Release Body

Use the following body for tag `v3.3.0` after the tagged hosted gates pass:

```markdown
## manga-director v3.3.0

v3.3.0 adds additive, typed, diagnostic-only Production Pipeline, Quality
Intelligence, Asset Lifecycle, Project Intelligence, and Governance surfaces.
It preserves documented public contracts from v1.x through v3.2.x and retains
StateMachine authority for the one-Page workflow.

See the migration guide and release validation assets for compatibility,
security, package, performance, and production-readiness evidence.
```
