# Agent Orchestration Design

## Task planning

A future planner creates a one-page-scoped `TaskPlanDTO` from existing
Workspace, Memory, Graph, Quality, and workflow evidence. Each task identifies
its human owner, suggested role, dependencies, required evidence, and approval
point. The plan is not executable.

## Delegation

Delegation is a recommendation with an explanation, capability match, and
human acceptance requirement. The proposed design must never automatically
select an agent, send a request, write an assignment, or take a workflow step.

## Parallel execution planning

Parallelism is a simulation only. A plan may identify independent analysis
tasks, but all tasks remain unstarted. Any future execution design must retain
the single-page invariant, isolate failures, avoid shared mutable context, and
return to the StateMachine for every transition.

## Conflict resolution

Conflicts are represented as explicit DTOs: conflicting references, severity,
affected role, alternatives, and a human resolution requirement. The platform
does not choose a resolution, mutate evidence, or hide disagreement.

## Result aggregation

Aggregation combines cited observations into a review packet. It preserves
provenance and omissions, marks unverified conclusions, and routes the packet
to a human checkpoint. It cannot persist, publish, trigger a Provider, or
complete review.

## Design validation

Every future orchestration implementation must prove no Core dependency, no
Repository write, no network dispatch, no automatic approval, no workflow
execution, and no request for multiple pages.
