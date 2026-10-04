# v3.4.0 Architecture Summary

v3.4.0 retains the inward dependency direction:

```text
CLI / FastAPI / MCP / Web UI
        -> Application DTO services (v3.4 Foundation, Intelligence, Governance)
        -> existing Knowledge Repository / Repository ports and WorkflowContext
        -> Core Domain / StateMachine / WorkflowEngine
```

Knowledge Platform, Production Operations, Organization Intelligence, Release
Intelligence, and Governance remain optional, immutable, non-executing
Application or Knowledge-layer projections. They do not write through a port,
own a workflow stage, invoke an agent or provider, approve a Page, deploy,
publish, or change StateMachine authority. Core, Infrastructure, Presentation,
Plugin, Extension SDK, Provider, and Image Backend boundaries are unchanged.
