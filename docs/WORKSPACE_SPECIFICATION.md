# Workspace Standard v1

## Scope

Workspace Standard v1 defines read-only production coordination for exactly
one existing page. It is represented by `V57ProductionWorkspaceService` and
the `ProductionWorkspaceV2Report` composition.

## Required invariants

- One and only one page is evaluated per workflow execution.
- Workflow stages are never skipped.
- Image generation requires an already persisted storyboard.
- Approval requires a completed quality review.
- StateMachine remains the sole transition authority.

## Report contract

Asset Registry, Project Workspace, Workflow State, Resource Manager, Template
Registry, and Production Session reports analyze supplied evidence. They do not
allocate resources, persist workspace state, resume a session, modify a
template, or execute a workflow.

## Compatibility

Repository persistence, workflow scheduling, project models, CLI, FastAPI,
MCP, Web UI, and previous Workspace APIs remain the source of truth. The v5.7
Workspace report can be omitted without changing v5.6 behavior.
