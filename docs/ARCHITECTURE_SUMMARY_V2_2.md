# v2.2.0 Architecture Summary

## Dependency direction

```text
Presentation (CLI / local MCP / Web UI)
            ↓
Application (Director / Project, Chapter, Batch, and Page Workflow Engines)
            ↓
Domain (StateMachine / Project / Page / Events)
            ↑
Ports (Repository / EventBus / ImageGenerator / LLMProvider)
            ↑
Infrastructure (file, SQLAlchemy, memory, adapters, plugins, SDK)
```

`Director` coordinates only. `WorkflowEngine` owns page-step execution and
delegates legal transitions to `StateMachine`. Agents remain stateless and do
not call each other. The StateMachine enforces one page per execution,
forward-only stages, storyboard-before-image, and quality-before-approval.

## Verified boundaries

- Workflow code depends on Repository protocols, not file or database adapters.
- Image and LLM provider selection remains registry/factory-based.
- Observability, health, diagnostics, notification, security, Plugin, and SDK
  behavior are outer-layer concerns and do not own page workflow logic.
- CLI and local MCP are composition/delivery adapters. The Web UI is separate.
- FastAPI/OpenAPI and Automation runtimes are not part of this source baseline.

Architecture, import-direction, dependency, public-export, and page-invariant
tests verify these constraints for v2.2.0.
