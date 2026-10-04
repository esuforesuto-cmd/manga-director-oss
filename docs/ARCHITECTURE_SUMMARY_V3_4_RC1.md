# v3.4.0 RC1 Architecture Summary

v3.4.0 RC1 retains the inward dependency direction:

```text
CLI / FastAPI / MCP / Web UI
        -> Application DTO services (v3.4 Foundation, Intelligence, Governance)
        -> existing public Repository port and WorkflowContext
        -> Core Domain / StateMachine / WorkflowEngine
```

Knowledge Platform, Production Operations, Organization Intelligence, Release
Intelligence, and Governance services are optional, non-executing Application
projections. They do not write, transition, generate, approve, invoke a
Provider or Agent, persist an audit, enforce policy, allocate, schedule,
retain, archive, delete, authorize, tag, sign, publish, deploy, or alter
StateMachine authority.

Core, Infrastructure, Presentation, Knowledge Repository, Plugin, Extension
SDK, Provider, Image Backend, and existing Repository boundaries remain
unchanged. Presentation adapters render shared DTOs only.
