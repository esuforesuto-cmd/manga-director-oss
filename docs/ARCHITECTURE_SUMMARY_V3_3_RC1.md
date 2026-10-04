# v3.3.0 RC1 Architecture Summary

v3.3.0 RC1 retains the inward dependency direction:

```text
CLI / FastAPI / MCP / Web UI
        -> Application DTO services (v3.3 Foundation, Intelligence, Governance)
        -> existing public Repository port and WorkflowContext
        -> Core Domain / StateMachine / WorkflowEngine
```

Production, Quality, Asset, Project, and Governance services are optional,
non-executing Application projections. They never write through the Repository,
own a workflow stage, invoke a Provider or Agent, enforce policy, approve a
Page, publish, schedule, allocate, retain, archive, delete, or alter
StateMachine authority.

Core, Infrastructure, Presentation, Knowledge-facing Repository boundaries,
Plugin, and Extension SDK boundaries remain unchanged. Presentation adapters
render shared DTOs only.
