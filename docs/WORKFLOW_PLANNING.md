# Workflow Planning

`WorkflowPlanner` is an optional Application-layer advisor. Given one
`WorkflowContext`, it returns an immutable `WorkflowPlanningReport` containing
an `ExecutionPlan`, dependency graph, complexity analysis, relative estimate,
and one StateMachine-derived recommendation.

It does not call an Agent, invoke `WorkflowEngine`, mutate context, persist a
Project, schedule work, or select an execution target. Legal next-state and
command information is read from `StateMachine`, so the forward-only one-page
workflow remains authoritative.

```python
from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.production import PlanningService, ProviderOrchestrator, WorkflowPlanner
from manga_director.workflow import WorkflowContext

service = PlanningService(
    planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
)
report = service.summary(WorkflowContext(page={"id": "page-1"}))
assert report.workflow.plan.execution_performed is False
```

`manga-director planning preview PROJECT PAGE` reads one persisted page and
prints the same DTO. It never advances that page.

