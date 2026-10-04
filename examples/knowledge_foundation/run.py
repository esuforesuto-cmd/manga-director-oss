"""Render a v3 Knowledge Foundation snapshot without repository writes."""

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.domain.project import Page, Project
from manga_director.production import (
    DirectorFoundationService,
    DirectorPlanningService,
    KnowledgeService,
    PlanningService,
    ProviderOrchestrator,
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository

repository = InMemoryRepository()
repository.save(Project(id="sample", title="Sample", pages=[Page(page_number=1)]))
planning = PlanningService(
    planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
)
service = DirectorPlanningService(DirectorFoundationService(planning, KnowledgeService(repository)), planning)
print(service.knowledge_dashboard().to_json())
