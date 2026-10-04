"""Render developer guidance without changing configuration or files."""

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.production import (
    CollaborationPlanningService,
    DirectorFoundationService,
    DirectorPlanningService,
    KnowledgeService,
    PlanningService,
    ProviderOrchestrator,
    V31FoundationService,
    V31InsightsService,
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository

repository = InMemoryRepository()
planning = PlanningService(
    planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
)
director = DirectorPlanningService(DirectorFoundationService(planning, KnowledgeService(repository)), planning)
foundation = V31FoundationService(director, CollaborationPlanningService(director), repository)
print(V31InsightsService(foundation, repository).developer_experience_dashboard({"profile": "testing"}).to_json())
