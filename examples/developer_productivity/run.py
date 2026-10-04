"""Render v3.1 template descriptors without generating workspace files."""

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

repository = InMemoryRepository()
planning = PlanningService(
    planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
)
foundation = DirectorPlanningService(DirectorFoundationService(planning, KnowledgeService(repository)), planning)
service = V31FoundationService(foundation, CollaborationPlanningService(foundation), repository)
print(service.developer_productivity_dashboard().to_json())
