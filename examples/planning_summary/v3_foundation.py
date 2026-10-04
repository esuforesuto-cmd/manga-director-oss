"""Render the compact v3 planning summary for one Page context."""

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.production import (
    DirectorFoundationService,
    DirectorPlanningService,
    KnowledgeService,
    PlanningService,
    ProviderOrchestrator,
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

planning = PlanningService(
    planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
)
service = DirectorPlanningService(
    DirectorFoundationService(planning, KnowledgeService(InMemoryRepository())), planning
)
print(service.planning_summary(WorkflowContext(page={"id": "sample-page"})).to_json())
