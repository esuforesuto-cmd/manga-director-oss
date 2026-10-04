"""Print a non-executing plan for exactly one Draft page."""

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.production import PlanningService, ProviderOrchestrator, WorkflowPlanner
from manga_director.workflow import WorkflowContext

service = PlanningService(
    planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
)
print(service.summary(WorkflowContext(page={"id": "example-page"})).to_markdown())
