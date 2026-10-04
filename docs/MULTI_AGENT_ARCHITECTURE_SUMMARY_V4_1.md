# v4.1.0 Multi-Agent Architecture Summary

The Multi-Agent Platform is an Application-layer, DTO-only extension.

```text
Existing ProjectRepository + one-page WorkflowContext
                    ↓ read-only evidence
Agent Registry → Runtime Preparation → Planning / Orchestration
                    ↓
Collaboration / Human Review / Governance / Observability / Reliability DTOs
                    ↓
CLI, FastAPI, MCP, and Web UI may present existing or additive DTOs
```

The platform does not replace existing workflow agents, invoke models, dispatch
tasks, modify repositories, or bypass quality-review and approval rules. Core
StateMachine and WorkflowEngine authority remains unchanged.
