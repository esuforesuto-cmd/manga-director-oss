# v3.2.0 RC1 Architecture Summary

The RC retains the inward dependency direction:

```text
CLI / FastAPI / MCP / Web UI
        -> Application DTO services (v3.2 Foundation, Insights, Assurance)
        -> existing public Repository port and WorkflowContext
        -> Core Domain / StateMachine / WorkflowEngine
```

Creative Studio, Asset Intelligence, Workflow Profiles, Production Analytics,
Workspace and Production Insights, Reliability, Governance, and Release
Readiness are optional non-executing Application services. They never write
through the Repository, own a workflow stage, invoke an Agent/Provider, approve
a Page, deploy, publish, or alter StateMachine authority.

Core, Infrastructure, Presentation, Knowledge, Analytics, Plugin, and Extension
SDK boundaries remain unchanged. Presentation adapters render shared DTOs only.
