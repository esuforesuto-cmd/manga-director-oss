"""Render a v3 Director Platform session without executing a workflow."""

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
print(service.director_platform(WorkflowContext(page={"id": "sample-page"})).to_json())
