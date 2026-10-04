# v2.3.0 Architecture Summary

```text
Presentation (CLI / local MCP / optional DTO FastAPI / Web UI)
                         |
                         v
Application (Director / Workflow / diagnostics composition)
                         |
                         v
Domain <- Ports (Repository / EventBus / Adapter Protocols) <- Infrastructure
```

v2.3.0 preserves Domain isolation, the narrow Page `WorkflowEngine`, the
`ProjectRepository` port, provider/backend protocols, and Plugin/Extension
outer boundaries. Observability receives injected safe snapshots and cannot
steer workflow execution. The optional FastAPI adapter returns DTOs only and
does not expose Domain models or call Agents directly.

The StateMachine remains the sole authority for page state transitions and
enforces exactly one page per execution, no skipped stage, storyboard before
generation, quality before approval, and explicit human approval.
