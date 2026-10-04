# v3.3.0 Architecture Summary

v3.3.0 retains the inward dependency direction:

```text
CLI / FastAPI / MCP / Web UI
        -> Application DTO services (v3.3 Foundation, Intelligence, Governance)
        -> existing public Repository port and WorkflowContext
        -> Core Domain / StateMachine / WorkflowEngine
```

Production Pipeline, Quality Intelligence, Asset Lifecycle, Project
Intelligence, and Governance are optional, immutable, non-executing
Application services. They do not write through the Repository, own a workflow
stage, invoke an Agent or Provider, approve a Page, deploy, publish, or alter
StateMachine authority. Core, Infrastructure, Presentation, Knowledge,
Analytics, Plugin, and Extension SDK boundaries remain unchanged.
