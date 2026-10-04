"""Render v3.1 Knowledge reliability evidence without repository mutation."""

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.domain.project import Page, Project
from manga_director.production import (
    CollaborationPlanningService,
    DirectorFoundationService,
    DirectorPlanningService,
    KnowledgeService,
    PlanningService,
    ProviderOrchestrator,
    V31AssuranceService,
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
service = V31AssuranceService(foundation, V31InsightsService(foundation, repository), repository)
print(service.knowledge_reliability_dashboard().to_json())
