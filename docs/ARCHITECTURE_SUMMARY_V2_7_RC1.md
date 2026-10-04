# v2.7.0 RC1 Architecture Summary

The established Clean Architecture is unchanged. Domain owns page-workflow
invariants; `WorkflowEngine` and `StateMachine` enforce one-page, forward-only
execution; Application services compose ports; Infrastructure implements
adapters and repositories; CLI, FastAPI, MCP, and Web UI remain outer delivery
adapters.

The v2.7 Director, Intelligence, and Reliability services are contained in
`manga_director.production`. They compose an existing `WorkflowContext`,
planning data, and the Repository port into frozen, transport-neutral DTOs.
They do not import a presentation adapter, mutate a project, invoke an Agent or
Provider, dispatch work, or add a Core dependency on delivery or scheduling.

Repository, Knowledge, Provider Runtime, Image Backend Runtime, Plugin, and
Extension SDK boundaries remain port- or protocol-based. The root public Python
API has not been widened; v2.7 helpers stay in the optional Production package.
