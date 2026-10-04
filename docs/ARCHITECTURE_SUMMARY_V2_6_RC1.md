# v2.6.0 RC1 Architecture Summary

The established clean architecture is unchanged: Domain owns page-workflow
invariants; `WorkflowEngine` and `StateMachine` enforce one-page forward-only
execution; Application services compose ports; Infrastructure implements
adapters and repositories; CLI, FastAPI, MCP, and Web UI are outer delivery
adapters.

The v2.6 services are contained in `manga_director.production`. They compose
existing workflow context, runtime metadata, configuration, repository, and
diagnostic ports into read-only DTOs. They do not import a Presentation adapter,
do not modify Domain state, and do not introduce a Core dependency on delivery,
network, provider execution, or scheduling.

Repository, Provider Runtime, Image Backend Runtime, Plugin, and Extension SDK
boundaries remain port- or protocol-based. The root public Python API has not
been widened; planning, analysis, governance, readiness, and dashboard APIs
stay in the optional Production package.
