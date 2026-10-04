# Agent Platform Design

## Scope

The proposed platform is an Application-layer planning model. It consumes
existing Project, Repository, WorkflowContext, diagnostics, and quality
evidence through current public boundaries. It must return transport-neutral
DTOs and must not invoke a model, agent, workflow, or write port.

## Agent Registry

The registry is an immutable catalogue proposal:

| Concept | Proposed fields | Prohibited authority |
| --- | --- | --- |
| Agent Profile | identifier, display name, role, status, provenance | start, stop, or execute an agent |
| Capability Model | capability name, inputs, limits, evidence requirements | discover remotely or select automatically |
| Role Definition | responsibility, review obligation, handoff contract | own a workflow stage or approval |
| Lifecycle | proposed, available, unavailable, retired | lifecycle transition persistence |
| Communication Protocol | message intent, DTO schema, correlation ID, visibility | network dispatch or hidden communication |

## Proposed service boundary

```text
CLI / FastAPI / MCP / Web UI
        -> Agent planning DTO service (future, additive)
        -> current ProjectRepository / WorkflowContext / diagnostics DTOs
        -> Core Domain / StateMachine / WorkflowEngine
```

The future service may produce a registry snapshot, capability matrix, and
planning recommendation. It must expose `planning_only=True`,
`execution_enabled=False`, and `automatic_action_taken=False` equivalents.

## Compatibility and rollout

Start with DTOs behind additive names. Do not change `Agent`, Plugin, Provider,
Extension SDK, Repository, CLI, FastAPI, MCP, or Web UI contracts. A later
implementation requires API snapshots, architecture tests, deterministic
fixtures, security review, and explicit approval of any execution authority.
