"""Render v3 Creative Knowledge without a new knowledge store or writes."""

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.domain.project import Page, Project
from manga_director.production import (
    CollaborationPlanningService,
    DirectorFoundationService,
    DirectorPlanningService,
    KnowledgeService,
    PlanningService,
    ProviderOrchestrator,
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository

repository = InMemoryRepository()
repository.save(Project(id="sample", title="Sample", pages=[Page(page_number=1)], metadata={"world": "hidden"}))
planning = PlanningService(
    planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
)
platform = DirectorPlanningService(DirectorFoundationService(planning, KnowledgeService(repository)), planning)
print(CollaborationPlanningService(platform).creative_knowledge_dashboard().to_json())
