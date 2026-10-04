# v3.1.0 Architecture Summary

Domain owns all page-workflow invariants. `WorkflowEngine` and `StateMachine`
execute exactly one Page and enforce legal forward-only transitions.

```text
CLI / FastAPI / MCP / Web UI
        -> Application DTO services (v3.1 Foundation, Insights, Assurance)
        -> existing Repository port and WorkflowContext
        -> Core Domain / StateMachine / WorkflowEngine
```

Creative Collaboration, Knowledge Evolution, Operations Platform, Developer
Productivity, Creative Review, Knowledge Analytics, Operations Intelligence,
and Assurance are optional, non-executing Application services. They do not
write through the Repository, own a workflow stage, invoke an Agent or Provider,
approve a Page, or alter StateMachine authority.

Core, Infrastructure, Presentation, Plugin, Extension SDK, Provider Runtime,
and Image Backend Runtime boundaries remain unchanged. Presentation adapters
render shared DTOs only.
