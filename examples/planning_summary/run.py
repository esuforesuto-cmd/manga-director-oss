"""Produce a portable planning diagnostic for a single page context."""

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.production import PlanningService, ProviderOrchestrator, WorkflowPlanner
from manga_director.workflow import WorkflowContext

summary = PlanningService(
    planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
).summary(WorkflowContext(page={"id": "example-page"}), configuration={"profile": "testing"})
print(summary.to_json())
