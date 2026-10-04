# v4.1 RC1 Architecture Summary

## Scope

The v4.1 modules are additive Application-layer DTO projections:

- `v4_1_agent_foundation.py` — local agent declarations, prepared runtime,
  collaboration, and communication evidence.
- `v4_1_orchestration.py` — one-page orchestration, planning, collaboration
  workflow, and conflict-resolution evidence.
- `v4_1_assurance.py` — human review, governance, observability, and reliability
  evidence.

## Boundary result

The modules depend only on domain DTOs, `WorkflowContext`, and the bounded local
agent registry. They do not depend on CLI, FastAPI, MCP, Web UI, Provider,
Backend, or repository write layers. They do not invoke agents or call `save`.

Core StateMachine authority, the one-page workflow invariant, persisted
storyboard prerequisite, completed quality-review prerequisite, and explicit
approval transition remain unchanged.
