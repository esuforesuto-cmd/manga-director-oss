"""Render v3 Director Intelligence without workflow mutation."""

from manga_director.adapters.runtime import LLMProviderRuntime
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
from manga_director.workflow import WorkflowContext

planning = PlanningService(
    planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
)
platform = DirectorPlanningService(
    DirectorFoundationService(planning, KnowledgeService(InMemoryRepository())), planning
)
print(CollaborationPlanningService(platform).director_intelligence_dashboard(WorkflowContext()).to_json())
