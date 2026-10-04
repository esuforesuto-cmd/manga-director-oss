"""Render a v3 Creative Planning report without image generation."""

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.production import (
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
service = DirectorPlanningService(
    DirectorFoundationService(planning, KnowledgeService(InMemoryRepository())), planning
)
context = WorkflowContext(
    page={"id": "sample-page"},
    artifacts={"page_design": {"purpose": "Set up a reveal", "panel_count": 2}},
)
print(service.creative_dashboard(context).to_json())
