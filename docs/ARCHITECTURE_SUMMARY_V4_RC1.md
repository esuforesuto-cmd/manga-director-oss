# v4.0.0 RC1 Architecture Summary

v4.0 RC1 retains the inward dependency direction:

```text
CLI / FastAPI / MCP / Web UI
        -> Application DTO services (v4 Foundation, Intelligence, Governance)
        -> existing public Repository port and WorkflowContext
        -> Core Domain / StateMachine / WorkflowEngine
```

Workspace, Memory, Graph, and Quality modules are additive Application and
Knowledge-layer projections. They do not write, transition, generate, approve,
invoke a Provider or Agent, persist an audit, enforce policy, retain memory,
repair graph evidence, or alter StateMachine authority.

Core, Infrastructure, Presentation, Repository, Plugin, Extension SDK,
Provider, Image Backend, and existing public boundaries are unchanged.
