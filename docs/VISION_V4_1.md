# v4.1 Vision: Creative Agent Platform

## Vision update

v4.1 plans a Creative Agent Platform that helps people organise creative work
without turning manga-director into an autonomous production system. Agents are
typed, explainable planning participants; they do not become workflow or
approval authorities.

## Production goals

- Make roles, capabilities, delegation proposals, and decision history visible.
- Preserve one-page workflow authority in the existing StateMachine.
- Make every proposed delegation reviewable, reversible, and attributable to a
  human decision.
- Keep planning evidence local and bounded until a separately approved storage
  design exists.

## Design principles

- Core, Repository interfaces, Workflow Engine, and current public contracts
  remain canonical.
- A future Agent Registry is a capability catalogue, not an execution runtime.
- Parallel work is modelled as a plan or simulation; it cannot run tasks or
  write results without explicit future authority.
- A human approval point is mandatory before any workflow-changing action.
- Decision history is an auditable DTO design, not a durable record in v4.1.

## Non-goals

Autonomous AI, automatic delegation, agent-to-agent execution, automatic
approval, workflow automation, Cloud SaaS, marketplace, distributed runtime,
new database schema, and Core redesign are not in v4.1 scope.

## Migration strategy

| Stage | Additive design outcome | Compatibility boundary |
| --- | --- | --- |
| Registry vocabulary | Define Agent Profile, Capability, Role, Lifecycle, and Protocol DTOs. | No executable Agent interface or public-contract replacement. |
| Collaboration planning | Describe Director, Editor, Writer, Artist, and Reviewer role proposals. | Existing human review and StateMachine gates remain authoritative. |
| Orchestration simulation | Produce task, delegation, parallelism, conflict, and aggregation plans. | No task dispatch, concurrency, mutation, or result persistence. |
| Human review | Model approval, feedback, override, and decision-history DTOs. | No approval automation or durable decision store. |

The planning baseline was `4.0.0`. The approved DTO-only foundations are now
reviewed in `4.1.0`; autonomous execution remains unauthorized.
