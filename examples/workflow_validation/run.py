"""Validate one Draft page without running its next workflow step."""

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.production import (
    PlanningService,
    ProviderOrchestrator,
    WorkflowDependencyAnalyzer,
    WorkflowPlanner,
    WorkflowReliabilityAnalyzer,
)
from manga_director.workflow import WorkflowContext

planning = PlanningService(
    planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
)
report = WorkflowReliabilityAnalyzer(
    planning, WorkflowDependencyAnalyzer(planning)
).report(WorkflowContext(page={"id": "example-page"}))
print(report.to_markdown())
