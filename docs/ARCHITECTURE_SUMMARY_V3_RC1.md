# v3.0.0 RC1 Architecture Summary

The established Clean Architecture is unchanged. Domain owns the page-workflow
invariants; `WorkflowEngine` and `StateMachine` enforce one-page, forward-only
execution. Application services compose ports. Infrastructure implements
adapters and repositories. CLI, FastAPI, MCP, and Web UI are outer delivery
adapters.

v3 Director, Creative, Knowledge, Collaboration, Review, and Readiness services
live in `manga_director.production`. They compose existing workflow context,
repository-port projections, and planning data into immutable,
transport-neutral DTOs. They do not import presentation adapters, mutate a
project, invoke an Agent or Provider, dispatch work, or add a Core dependency.

Repository, Plugin, Extension SDK, Provider Runtime, and Image Backend Runtime
boundaries remain port- or protocol-based. The root public API has not widened;
v3 helpers remain optional Production-package APIs. No layer violation or
circular production dependency was identified in the RC audit.
