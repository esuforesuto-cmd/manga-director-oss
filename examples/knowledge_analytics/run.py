"""Render redacted Knowledge analytics without writing to the Repository."""

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.domain.project import Page, Project
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
repository.save(Project(id="sample", title="Sample", pages=[Page(page_number=1)], metadata={"world": "redacted"}))
planning = PlanningService(
    planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
)
director = DirectorPlanningService(DirectorFoundationService(planning, KnowledgeService(repository)), planning)
foundation = V31FoundationService(director, CollaborationPlanningService(director), repository)
print(V31InsightsService(foundation, repository).knowledge_analytics_dashboard().to_json())
