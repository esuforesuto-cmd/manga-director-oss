# v3.5.0 Architecture Summary

v3.5.0 retains the inward dependency direction:

```text
CLI / FastAPI / MCP / Web UI
        -> Application DTO services (v3.5 Foundation, Intelligence, Governance)
        -> existing public Repository port and WorkflowContext
        -> Core Domain / StateMachine / WorkflowEngine
```

Unified Knowledge Graph, Creative Intelligence, Production Intelligence,
Platform Analytics, and Governance remain optional, immutable, non-executing
Application or Knowledge-layer projections. They do not write through a port,
own a workflow stage, invoke an Agent or Provider, approve a Page, persist an
audit, enforce policy, deploy, publish, or change StateMachine authority.

Core, Infrastructure, Presentation, Plugin, Extension SDK, Provider, Image
Backend, and existing Repository boundaries are unchanged.
