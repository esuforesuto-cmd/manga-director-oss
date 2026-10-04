# v5.7 Platform Architecture

## Scope

The v5.7 Platform Plane is an Application-layer composition design. It reads
existing project, workflow, asset, review, and plugin evidence and returns
transport-neutral DTOs. Domain state, storage, plugin lifecycle, and delivery
adapters retain their current owners.

```text
CLI / FastAPI / MCP / Web UI / Python SDK
                 |
                 v
      Platform query and report services (v5.7 Foundation)
                 |
                 v
 Workspace | Collaboration | Asset | Automation | Plugin descriptors
                 |
                 v
 Existing Project, WorkflowContext, Asset DTOs, Plugin Registry, reports
                 |
                 v
 StateMachine / Repository / Plugin lifecycle / existing adapters
```

## Responsibility boundaries

| Platform area | Planned responsibility | Retained owner |
| --- | --- | --- |
| Production Platform | Compose supplied production evidence. | Existing Engines and workflow. |
| Asset Management | Describe catalog, version, relationship, and lifecycle evidence. | Existing Asset DTOs and Repository interfaces. |
| Project Workspace | Group references and human work context. | Project and Page aggregates. |
| Collaboration | Record advisory assignments and reviews. | Human approval and existing review workflow. |
| Automation | Validate declarative template/rule evidence. | StateMachine and WorkflowEngine. |
| Plugin Ecosystem | Describe compatible capabilities and provenance. | Existing PluginManifest, PluginRegistry, and PluginManager. |

## Invariants

Every workflow execution remains exactly one Page. The StateMachine owns legal
transitions; a persisted storyboard remains required before generation; and a
completed quality review remains required before human approval. Platform
services cannot execute, advance, save, register, load, or publish anything.

## Iteration 1 foundation

`manga_director.production.v5_7_platform_foundation` is a transport-neutral
Application-layer composition module. It provides Workspace Manager, Project
Manager, Asset Manager, Automation Foundation, and Plugin Runtime reports from
one existing `WorkflowContext` and an optional read-only plugin-registry view.
It owns no lifecycle state and has no delivery, repository, workflow-engine,
or plugin-manager dependency.

## Iteration 2 production workspace

`manga_director.production.v5_7_production_workspace` composes Foundation
reports with caller-supplied resource and template descriptors. Asset Registry,
Project Workspace, Workflow State Manager, Resource Manager, Template Registry,
and Production Session Manager are diagnostic-only. They rely on the existing
StateMachine for transition authority and do not allocate, persist, resume,
load, apply, or execute anything.

## Iteration 3 production platform

`manga_director.production.v5_7_production_platform` composes existing
Production Pipeline, Export Engine, and v5.7 workspace diagnostics. Its
Automation Pipeline, Plugin Lifecycle, Event Bus, Task Scheduler, Snapshot,
and Analytics DTOs are observational or eligibility-only. Existing runtime
owners retain all execution, event delivery, plugin lifecycle, scheduling,
snapshot persistence, workflow transition, approval, export, and publication
responsibilities.

## Adapter strategy

Future adapters add query/report endpoints only. Existing CLI commands, REST
routes, MCP tools, Web UI contracts, SDK methods, and repository interfaces are
not renamed or removed. Any implementation must be independently compatible
with callers that do not supply v5.7 metadata.
