"""Render v3 Director Reliability evidence without workflow execution."""

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.production import (
    CollaborationPlanningService,
    DirectorFoundationService,
    DirectorPlanningService,
    KnowledgeService,
    PlanningService,
    ProviderOrchestrator,
    V3ReadinessService,
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

planning = PlanningService(planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime()))
foundation = DirectorPlanningService(DirectorFoundationService(planning, KnowledgeService(InMemoryRepository())), planning)
print(V3ReadinessService(foundation, CollaborationPlanningService(foundation)).director_executive(WorkflowContext()).to_json())
