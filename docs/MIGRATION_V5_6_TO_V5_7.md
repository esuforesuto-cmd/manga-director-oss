# Migration Strategy: v5.6 to v5.7

v5.7 planning is additive and requires no installation action, data conversion,
configuration update, endpoint change, CLI migration, MCP migration, Web UI
migration, repository-interface change, plugin migration, or workflow migration.

Future adopters may opt in to platform report services by supplying existing
one-page `WorkflowContext`, project, asset, review, automation, and plugin
evidence. Callers that omit v5.7 metadata retain v5.6 behavior unchanged.

Iteration 1 introduces optional Workspace Manager, Project Manager, Asset
Manager, Automation Foundation, and Plugin Runtime reports. They are
read-only projections and require neither a data migration nor a change to
PluginRegistry, PluginManager, Automation Engine, WorkflowEngine, or the
Repository interface.

Iteration 2 adds optional Production Workspace v2 diagnostics. Resource and
template descriptors are caller-supplied; Asset Registry and Session Recovery
reports are observational. No workflow state, project, asset, session,
template registry, CLI, FastAPI, MCP, Web UI, or plugin lifecycle migration is
required.

Iteration 3 adds optional Production Orchestrator reports. They compose
existing one-page production, review, export, workspace, event, and Plugin
evidence without changing CLI, FastAPI, MCP, Web UI, SDK, StateMachine,
Workflow Engine, EventBus, PluginManager, Repository, or delivery behavior.

Rollback consists of stopping use of the optional report calls. The StateMachine
remains authoritative throughout planning and all future implementation.
