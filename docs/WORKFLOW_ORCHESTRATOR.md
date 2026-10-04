# Workflow Orchestrator

## v6.0 Iteration 2 foundation

The Workflow Orchestrator is a read-only recommendation surface. It reuses the
existing `StateMachine` through v5.7 workflow diagnostics and reports the
single legal next command, if one exists.

It cannot dispatch that command, skip a stage, create a page, mutate workflow
state, or approve a Page. Human review remains required and the domain
StateMachine remains the transition authority.

## Compatibility

The feature adds no Workflow Engine behavior and changes no CLI, FastAPI, MCP,
Web UI, Repository, or public v5.x workflow interface.
