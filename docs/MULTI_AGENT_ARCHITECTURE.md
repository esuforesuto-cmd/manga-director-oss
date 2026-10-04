# Multi-Agent Architecture Design

## Layering

Multi-agent planning belongs above the current Application services. It cannot
be imported by Core modules and cannot replace the existing Workflow Engine.

```text
Presentation adapters
        -> Agent platform planning DTOs
        -> Creative Workspace / Memory / Graph / Quality projections
        -> current Repository ports and WorkflowContext
        -> Core StateMachine and WorkflowEngine
```

## Lifecycle model

`proposed -> reviewed -> available -> unavailable -> retired` is a descriptive
lifecycle for registry entries. It is not a runtime scheduler and has no
automatic transition. A human owner reviews each state change in a future
approved persistence design.

## Communication model

Messages are proposed immutable DTO envelopes with sender role, recipient role,
intent, correlation ID, references, and visibility. They carry no hidden prompt
state, secret, executable command, or authority to act. A future transport must
be opt-in, authenticated, auditable, and separately designed.

## Safety constraints

No proposed agent may request multiple pages, skip a StateMachine stage,
generate before storyboard persistence, or approve before quality review. The
existing state machine validates every actual transition.
