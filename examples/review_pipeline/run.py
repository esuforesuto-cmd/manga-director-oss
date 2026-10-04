"""Render v3 Review Pipeline diagnostics without quality approval."""

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
print(CollaborationPlanningService(platform).review_pipeline_dashboard(WorkflowContext()).to_json())
