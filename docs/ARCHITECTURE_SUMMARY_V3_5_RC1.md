# v3.5.0 RC1 Architecture Summary

v3.5.0 RC1 retains the inward dependency direction:

```text
CLI / FastAPI / MCP / Web UI
        -> Application DTO services (v3.5 Foundation, Intelligence, Governance)
        -> existing public Repository port and WorkflowContext
        -> Core Domain / StateMachine / WorkflowEngine
```

Unified Knowledge Graph, Creative Intelligence, Production Intelligence,
Platform Analytics, and Governance are optional, non-executing Application and
Knowledge-layer projections. They do not write, transition, generate, approve,
invoke a Provider or Agent, persist an audit, enforce policy, allocate,
schedule, remediate, deploy, monitor, authorize, tag, sign, publish, or alter
StateMachine authority.

Core, Infrastructure, Presentation, Repository, Knowledge Repository, Plugin,
Extension SDK, Provider, Image Backend, and existing public boundaries are
unchanged. Presentation adapters render shared DTOs only.
