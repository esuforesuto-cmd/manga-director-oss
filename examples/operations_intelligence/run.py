"""Render one-Page operations intelligence without operational changes."""

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
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
planning = PlanningService(
    planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
)
director = DirectorPlanningService(DirectorFoundationService(planning, KnowledgeService(repository)), planning)
foundation = V31FoundationService(director, CollaborationPlanningService(director), repository)
service = V31InsightsService(foundation, repository)
print(service.operations_intelligence_dashboard(WorkflowContext(page={"id": "sample-page"})).to_json())
