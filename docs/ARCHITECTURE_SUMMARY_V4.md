# v4.0.0 Architecture Summary

v4.0.0 retains the inward dependency direction:

```text
CLI / FastAPI / MCP / Web UI
        -> Application DTO services (v4 Foundation, Intelligence, Governance)
        -> existing public Repository port and WorkflowContext
        -> Core Domain / StateMachine / WorkflowEngine
```

Creative Workspace, Memory, Graph, Quality, Intelligence, and Governance remain
optional, immutable, non-executing Application or Knowledge-layer projections.
They do not write through a port, own a workflow stage, invoke an Agent or
Provider, approve a Page, persist an audit, enforce policy, retain memory,
repair graph evidence, or change StateMachine authority.

Core, Infrastructure, Presentation, Plugin, Extension SDK, Provider, Image
Backend, and existing Repository boundaries are unchanged.
