"""Render redacted Knowledge Evolution evidence from an in-memory repository."""

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
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository

repository = InMemoryRepository()
repository.save(Project(id="sample", title="Sample", pages=[Page(page_number=1)], metadata={"world": "redacted"}))
planning = PlanningService(
    planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
)
foundation = DirectorPlanningService(DirectorFoundationService(planning, KnowledgeService(repository)), planning)
service = V31FoundationService(foundation, CollaborationPlanningService(foundation), repository)
print(service.knowledge_evolution_dashboard().to_json())
