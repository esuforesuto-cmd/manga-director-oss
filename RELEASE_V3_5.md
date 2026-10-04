# manga-director v3.5.0

## What's New

v3.5.0 promotes the reviewed RC1 scope without adding features. It provides
typed, local, read-only Unified Knowledge Graph, Creative Intelligence,
Production Intelligence, Platform Analytics, and Governance reports. The Core
Domain, StateMachine, Workflow Engine, Repository port, and existing public
contracts remain unchanged.

## Unified Knowledge Graph

Node, edge, context, trace, coverage, relationship, recommendation, health,
and governance DTOs read existing Repository evidence only. They do not persist
a graph, search remotely, merge, repair, or change Repository authority.

## Creative Intelligence

Story, character, Page Quality, trend, recommendation, and governance DTOs
support human review. They do not generate content, alter creative inputs,
complete a quality review, or approve a Page.

## Production Intelligence

Pipeline, efficiency, capacity, delivery risk, optimization, and governance
reports expose one-Page production evidence. They do not schedule, allocate,
modify a workflow, remediate, deploy, or make a delivery commitment.

## Platform Analytics and Governance

Cross-platform KPI, historical, regression, executive, health, policy,
compliance, audit, and dashboard DTOs aggregate supplied local evidence. They
do not collect remotely, monitor, retain telemetry, enforce policy, authorize a
release, or take an external action.

## Performance and Reliability

Provider-free benchmark smoke covers v3.5 graph, analytics, dashboards,
Repository, and reporting projections. The one-Page workflow, recovery,
configuration, diagnostics, health, Plugin, Extension SDK, and Repository
integrity boundaries are unchanged.

## Developer Experience

The same typed DTOs are available through optional CLI, FastAPI, and MCP
surfaces. The canonical version lives in `manga_director._version`; package
metadata derives from it, while OpenAPI and MCP derive it at runtime.

## Compatibility and Migration

v3.5.0 preserves documented v1.x, v2.0.x-v2.7.x, and v3.0.x-v3.4.x Python API,
CLI, FastAPI/REST, MCP, Workflow, Repository, Extension SDK, Plugin, Provider,
Backend, Automation, Notification, and Web UI contracts. No data, schema,
configuration, Repository, or workflow migration is required. See
[Migration](docs/MIGRATION_V3_5.md) and
[Compatibility](docs/COMPATIBILITY_V3_5.md).

## Known Limitations

Autonomous AI, workflow execution or approval automation, new Providers or
Backends, Cloud services, marketplace, and distributed runtime are out of
scope. v3.5 reports cannot bypass StateMachine authority, skip a stage, approve
a Page without completed quality review, or generate multiple Pages.

## Roadmap v3.6

The next cycle remains planning-led. Any v3.6 candidate must be opt-in,
additive, evidence-led, and retain one-Page workflow authority, compatibility,
security, performance, production, and governance validation.

## GitHub Release Notes

```markdown
## manga-director v3.5.0

v3.5.0 promotes the RC1-reviewed Unified Knowledge Graph, Creative
Intelligence, Production Intelligence, Platform Analytics, and Governance DTO
surfaces. It preserves documented public contracts from v1.x through v3.4.x and
retains StateMachine authority for the one-Page workflow.

No migration is required. See the migration guide and release validation assets
for compatibility, security, package, performance, and governance evidence.
```
