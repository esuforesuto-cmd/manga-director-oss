# manga-director v3.4.0

## What's New

v3.4.0 promotes the reviewed RC1 scope without adding features. It provides
typed, read-only reports for Knowledge Platform, Production Operations,
Organization Intelligence, Release Intelligence, and Governance. Core Domain,
StateMachine, Workflow Engine, Repository port, and existing public contracts
remain unchanged.

## Knowledge Platform

Catalog, classification, relationship, quality, index, insight, intelligence,
and governance DTOs read through the existing Knowledge Repository boundary.
They do not write knowledge, create storage, or change repository authority.

## Production Operations

Operations status, capacity, timelines, efficiency, bottleneck, optimization,
and governance reports make production evidence visible. They do not operate a
pipeline, allocate work, deploy, or advance a workflow stage.

## Organization Intelligence

Team-health, role, workload, collaboration, risk, analytics, and governance
DTOs support human planning. They do not manage people, assign work, or make
autonomous decisions.

## Release Intelligence

Release health, deployment, compatibility, regression, trend, forecast, and
governance reports are advisory release evidence. They do not publish an
artifact, create a tag, or grant release approval.

## Governance

Knowledge, Production, Organization, and Release policy, compliance, audit,
retention, and dashboard DTOs are inspection-only. Human review and the
existing StateMachine remain authoritative.

## Production and Performance Improvements

v3.4 retains transport-neutral production runtime, observability, diagnostics,
reporting, recovery, repository integrity, health, and configuration validation
boundaries. Provider-free benchmark smoke covers the additive v3.4 projection
paths without changing the one-Page workflow or promising hardware-independent
latency.

## Developer Experience

The same typed DTOs are available through optional CLI, FastAPI, and MCP
surfaces. The canonical Python version is `manga_director._version`; package
metadata derives from it, and OpenAPI/MCP derive it at runtime. The frontend
and SBOM carry the matching stable release value.

## Compatibility

v3.4.0 preserves documented v1.x, v2.0.x-v2.7.x, v3.0.x-v3.3.x Python API,
CLI, FastAPI/REST, MCP, workflow, Repository, Knowledge, Creative, Asset,
Analytics, Review, Diagnostics, Reporting, Governance, Operations, Health,
Plugin, Extension SDK, Provider, Image Backend, Automation, and Notification
contracts. No data, schema, configuration, Repository, or workflow migration is
required. See [Migration](docs/MIGRATION_V3_4.md) and
[Compatibility](docs/COMPATIBILITY_V3_4.md).

## Known Limitations

Autonomous AI, workflow execution or approval automation, new Providers or
Backends, Cloud services, marketplace, and distributed runtime are out of
scope. v3.4 reports cannot bypass StateMachine authority, skip a stage, approve
a Page without quality review, or generate multiple Pages.

## Roadmap v3.5

The next cycle will be planned publicly. Any work remains opt-in, additive, and
evidence-led, with one-Page workflow authority, compatibility, security,
production, and governance validation retained.

## GitHub Release Body

Use this body for tag `v3.4.0` after the tagged hosted gates pass:

```markdown
## manga-director v3.4.0

v3.4.0 promotes the RC1-reviewed, typed, diagnostic-only Knowledge Platform,
Production Operations, Organization Intelligence, Release Intelligence, and
Governance surfaces. It preserves documented public contracts from v1.x through
v3.3.x and retains StateMachine authority for the one-Page workflow.

See the migration guide and release validation assets for compatibility,
security, package, performance, production, enterprise, and governance
evidence.
```
