# v6.0 Platform Architecture

## Target shape

```text
CLI / FastAPI / MCP / Web UI / SDK
                |
                v
   v6 Application services and query/report DTOs
                |
   +------------+-------------+-------------+
   |            |             |             |
Workspace  Collaboration   Knowledge   Automation / Extension
   |            |             |             |
   +------------+-------------+-------------+
                v
Existing Project, WorkflowContext, Engines, Plugin APIs, Repository ports
                |
                v
StateMachine and existing infrastructure authorities
```

## Architecture rules

| Area | v6 responsibility | Retained authority |
| --- | --- | --- |
| Platform Core | Compose platform-level references and reports. | Existing public API and runtime. |
| Workspace Engine | Coordinate workspace views and snapshots. | Project/Page models and StateMachine. |
| Collaboration Engine | Record advisory tasks, reviews, and decisions. | Human approval workflow. |
| Knowledge Engine | Link provenance-bearing knowledge references. | Existing repositories and asset owners. |
| Automation Engine | Validate declarative plans and events. | Workflow Engine and policy owner. |
| Plugin Runtime | Describe compatible capabilities. | PluginManifest, PluginRegistry, PluginManager. |

## Boundaries

v6 services are Application-layer additions and depend inward on existing
domain contracts. Delivery adapters may expose opt-in query/report endpoints
only after the corresponding service is stable. New services do not import
delivery adapters, repositories, workflow engine internals, or PluginManager
implementation details.

## Scalability strategy

Use identifiers, summaries, pagination, bounded graph traversal, immutable
snapshots, and asynchronous *planning* records. Do not duplicate raw project
or asset payloads in cross-project reports. Runtime execution, persistence,
and queueing remain future implementation decisions behind ports.
