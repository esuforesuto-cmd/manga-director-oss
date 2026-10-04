# manga-director v4.0.0

## What's New

v4.0.0 promotes the reviewed RC1 scope without adding features. It provides
typed, local, read-only Creative Workspace, Creative Memory, Creative Knowledge
Graph, Creative Quality, Intelligence, and Governance reports. The Core Domain,
StateMachine, Workflow Engine, Repository port, and existing public contracts
remain unchanged.

## Creative Workspace and Memory

Workspace/session/snapshot/timeline and story/character/world/style/production
memory DTOs provide bounded Project and WorkflowContext evidence. They do not
persist a workspace or memory store, retrieve remotely, retain data, or change
source evidence.

## Creative Knowledge Graph

Node, edge, Story Graph, Character Graph, relationship, dependency, integrity,
and governance DTOs derive from existing Repository evidence only. They do not
persist, merge, repair, or replace a graph or Repository port.

## Creative Quality

Story, character, visual, editorial, intelligence, and governance DTOs support
human review. They do not generate content, alter creative inputs, complete a
quality review, enforce quality, or approve a Page.

## Performance and Reliability

Provider-free benchmark smoke covers v4 Workspace, Memory, Graph, Quality,
Intelligence, Governance, Repository, and reporting projections. The one-page
workflow, recovery, diagnostics, health, Plugin, Extension SDK, and Repository
integrity boundaries remain unchanged.

## Developer Experience

The canonical version lives in `manga_director._version`; package metadata
derives from it, while OpenAPI and MCP derive it at runtime. Frontend metadata
uses the matching stable `4.0.0` npm version.

## Compatibility and Migration

v4.0.0 preserves documented v1.x, v2.x, and v3.x-v3.5 Python API, CLI,
FastAPI/REST, MCP, Workflow, Repository, Extension SDK, Plugin, Provider,
Backend, Automation, Notification, and Web UI contracts. No data, schema,
configuration, Repository, or workflow migration is required. See
[Migration](docs/MIGRATION_V4.md) and [Compatibility](docs/COMPATIBILITY_V4.md).

## Known Limitations

Autonomous AI, workflow execution or approval automation, persistent
workspace/memory/graph storage, policy enforcement, automatic remediation, new
Providers or Backends, Cloud services, marketplace, and distributed runtime are
out of scope. v4 reports cannot bypass StateMachine authority, skip a stage,
approve a Page without completed quality review, or generate multiple Pages.

## Roadmap v4.1 Candidate

The next cycle remains planning-led. Any v4.1 candidate must be opt-in,
additive, evidence-led, and retain one-page workflow authority, compatibility,
security, performance, production, and governance validation.

## GitHub Release Notes

```markdown
## manga-director v4.0.0

v4.0.0 promotes the RC1-reviewed Creative Workspace, Creative Memory,
Creative Knowledge Graph, Creative Quality, Intelligence, and Governance DTO
surfaces. It preserves documented public contracts through v3.5 and retains
StateMachine authority for the one-page workflow.

No migration is required. See the migration guide and release validation assets
for compatibility, security, package, performance, and governance evidence.
```
