# AI Director Platform

## Purpose

The AI Director Platform is an application-layer planning boundary. It helps a
human compare legal next-step options and creative constraints; it is not an
autonomous Director, scheduler, or workflow executor.

## Planned contracts

| DTO | Contains | Safety boundary |
| --- | --- | --- |
| Goal | Human-authored objective, scope, priority, and success criteria. | Cannot contain an execution instruction. |
| Task graph | Dependencies, checkpoints, ownership, and StateMachine evidence. | One execution recommendation only. |
| Execution strategy | Ordered advisory options, assumptions, risks, and estimate. | Does not dispatch or call an Agent. |
| Decision trace | Public rationale, cited facts, policy inputs, and alternatives. | No hidden reasoning, secrets, or authorization. |
| Review strategy | Required editorial, continuity, quality, and human checkpoints. | Cannot approve a Page. |
| Iteration plan | Proposed revision and learning loop. | Does not mutate a Project or re-run a stage. |

## Issue backlog

| ID | Scope | Priority | Exit evidence |
| --- | --- | --- | --- |
| V3-DIR-01 | Director Planning and Goal Management. | P0 | Typed, immutable plan DTO and StateMachine-derived legal-step fixture. |
| V3-DIR-02 | Task Graph and Creative Planning. | P0 | Dependency graph proves a single Page execution boundary. |
| V3-DIR-03 | Execution Strategy and Decision Trace. | P1 | Alternatives, assumptions, risk, and public evidence render JSON/Markdown. |
| V3-DIR-04 | Review Strategy. | P1 | Existing quality and approval checkpoints are visible and non-bypassable. |
| V3-DIR-05 | Iteration Planning. | P1 | A revision plan is advisory and same-state re-execution remains explicit. |
| V3-DIR-06 | Director policy and recommendation tests. | P0 | No Agent, Provider, repository mutation, or state transition in tests. |

## Director decision flow

```text
Human goal + existing Page context + policy
                 ↓
      StateMachine legal-step evidence
                 ↓
  advisory strategy / task graph / decision trace
                 ↓
human chooses an existing CLI, API, MCP, or UI action
                 ↓
          existing WorkflowEngine execution
```

The final arrow is deliberately outside the Director Platform. The Platform
does not call it.

## Compatibility and policy

- `Director` remains a coordinator and owns no state transition logic.
- `WorkflowEngine` remains the sole component that can call an Agent.
- The platform uses existing Repository, EventBus, factory, and StateMachine
  read boundaries; it adds no provider-specific switch.
- A recommendation must identify required storyboard, quality, and approval
  guards, and must never recommend generating more than one Page.

See [Director Platform example](../examples/director_platform/README.md) and
[Director Planning validation](QUALITY_GATES.md).
