# v4 Architecture Planning

## Status

v4 is a staged migration plan on the `3.5.x` development branch. It does not
change Core Architecture, public APIs, Workflow execution, Repository
interfaces, persistence formats, or presentation ownership.

## Planned Platforms

| Platform | Responsibility | Prohibited authority |
| --- | --- | --- |
| Creative Workspace 2.0 | Unified workspace/session/state/snapshot/timeline views. | Workspace persistence, workflow transition, assignment, or approval. |
| Creative Memory | Story, character, world, style, and production-memory projections. | New memory store, remote retrieval, mutation, or retention enforcement. |
| Creative Knowledge Graph | Story, character, asset, relationship, and timeline graph projections. | Graph storage, merge, repair, remote search, or Repository replacement. |
| Creative Quality Platform | Story/character/visual/narrative/editorial quality evidence. | Automated review completion, creative edits, or approval. |

## Dependency Direction

```text
CLI / FastAPI / MCP / Web UI
        -> optional v4 Application / Knowledge DTO services
        -> existing v3.5 public Repository ports and WorkflowContext
        -> Core Domain / StateMachine / WorkflowEngine
```

No Core module imports a v4 module. Presentation adapters render shared DTOs
only. Repository ports remain canonical; WorkflowEngine remains the only
Agent-execution path.

## Invariants

Every future v4 Issue must preserve exactly one Page per workflow execution,
must never skip a StateMachine stage, must require a persisted storyboard before
image generation, and must require completed quality review before approval.
