# Multi-Agent Collaboration Design

## Scope

Multi-agent collaboration is a planning and review model only. It describes
roles, hand-offs, dependencies, and conflicts; it does not implement an agent
runtime, agent-to-agent calls, autonomous execution, or delegation.

## Proposed capability catalog

| Proposed role | Planned responsibility | Required human / workflow boundary |
| --- | --- | --- |
| Editor Agent | Editorial intent, pacing, and reader-impact recommendations. | Review strategy only; cannot approve. |
| Story Agent | Story-beat and chapter-context analysis. | Does not change Page state. |
| Scenario Agent | Scene objective, causality, and dialogue-context planning. | Does not write directly to persistence. |
| Character Agent | Character continuity and relationship evidence. | Uses redacted knowledge projections. |
| Storyboard Agent | Panel-level planning and storyboard completeness evidence. | The existing storyboard stage remains authoritative. |
| Prompt Agent | Prompt-pipeline compatibility and asset-intent planning. | Cannot generate an image. |
| Art Director Agent | Visual direction, composition, and consistency recommendations. | Does not invoke an image backend. |
| Review Agent | Quality, continuity, and risk aggregation. | Does not auto-pass or approve. |
| Coordinator Agent | Capability assignment and review-order proposal. | Does not call agents or dispatch tasks. |

## Collaboration contract

1. A coordinator emits a **proposed** task graph with declared inputs, output
   DTOs, owner, review checkpoint, and conflict policy.
2. Every proposed role remains compatible with the common `Agent.execute`
   interface if it is later implemented.
3. Agent instances never call each other. A future execution path must still
   be mediated by `WorkflowEngine` for exactly one Page.
4. Conflicts are reported as alternatives for a human reviewer; no role wins
   automatically.
5. Provider and image capabilities are metadata only during planning.

## Issue backlog

| ID | Design item | Priority | Dependency |
| --- | --- | --- | --- |
| V3-MA-01 | Capability descriptor and role catalog. | P1 | V3-DIR-01 |
| V3-MA-02 | Coordinator task-graph and hand-off DTO. | P1 | V3-MA-01 |
| V3-MA-03 | Review-order and conflict-resolution policy design. | P1 | V3-MA-02, V3-DIR-04 |
| V3-MA-04 | Deterministic multi-agent simulation fixtures. | P2 | V3-MA-03 |
| V3-MA-05 | Plugin / Extension SDK compatibility guide. | P2 | V3-MA-01 |

## Explicit exclusions

No multi-agent issue may introduce background workers, task queues, direct
messages, shared mutable memory, automatic provider calls, or a multi-page
execution request. The Page StateMachine guards are unchanged.

See [Multi-agent planning example](../examples/multi_agent/README.md).
