# Workflow Intelligence

Workflow intelligence is diagnostic-only. `PlanningService.workflow_intelligence`
returns a typed summary, observed persisted timeline, remaining execution graph,
bottleneck report, and advisory optimization recommendations.

The report can highlight missing persisted storyboard evidence for a
PromptBuilt-or-later page and high local context complexity. It does not repair
artifacts, change state, run an Agent, execute a Provider, or approve a page.
Its scope is always exactly one Page context.

Use `PlanningSummary.to_json()` for tooling and `to_markdown()` for review
artifacts. The summary includes an architecture preview that records the fixed
boundaries: Core and WorkflowEngine unchanged, Provider invocation disabled,
and scheduling disabled.

## v3 Foundation

`DirectorPlanningService.workflow_intelligence()` adds a separate, additive
v3 DTO surface: `PlanningDependencyGraph`, `CreativeProgressReport`,
`ExecutionTimeline`, and an advisory `WorkflowRecommendation`. It is composed
from the existing Director and Planning services, so it still derives legal
steps from the StateMachine and does not alter `WorkflowEngine`.

It is available through `manga-director director intelligence`, `GET
/v3/workflow`, and the `workflow_intelligence` MCP tool. The report is
diagnostic only: `workflow_modified` and `execution_performed` remain false.

See [Workflow Intelligence example](../examples/workflow_intelligence/run.py).
