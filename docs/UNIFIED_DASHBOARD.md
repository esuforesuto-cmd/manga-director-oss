# Unified Dashboard

## Scope

`unified_dashboard()` combines Unified Platform Analytics, Service
Orchestration, Operational Insights, and Lifecycle Analytics into a
transport-neutral `UnifiedDashboardReport`. It is the additive application API
for a caller that already has a project id and `WorkflowContext`.

## Integration model

The dashboard composes immutable reports in memory and records
`public_api_additive=True`. It does not replace the existing API, Runtime,
CLI, FastAPI/REST, MCP, Web UI, Repository, Workflow, Plugin/Extension SDK,
Provider, or Backend surface. Presentation adapters may adopt it in a future
compatible issue, but this iteration registers no route, tool, command, or UI.

## Operational boundary

The dashboard is not persisted or published and has no presentation dependency.
It cannot collect telemetry, begin monitoring, route a service, run a
Workflow, dispatch an Agent, accept an approval, enforce policy, or take a
cross-domain action. Every workflow-related dashboard remains one-Page scoped
under StateMachine authority.
