"""Render local operations metrics without starting an operation."""

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.production import (
    CollaborationPlanningService,
    DirectorFoundationService,
    DirectorPlanningService,
    KnowledgeService,
    PlanningService,
    ProviderOrchestrator,
    V31FoundationService,
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
planning = PlanningService(
    planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
)
foundation = DirectorPlanningService(DirectorFoundationService(planning, KnowledgeService(repository)), planning)
service = V31FoundationService(foundation, CollaborationPlanningService(foundation), repository)
print(service.operations_dashboard(WorkflowContext(page={"id": "sample-page"})).to_json())
