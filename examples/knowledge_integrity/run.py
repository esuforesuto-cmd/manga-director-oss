"""Render v3 Knowledge Integrity evidence without repository mutation."""

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

planning = PlanningService(planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime()))
foundation = DirectorPlanningService(DirectorFoundationService(planning, KnowledgeService(InMemoryRepository())), planning)
print(V3ReadinessService(foundation, CollaborationPlanningService(foundation)).knowledge_executive().to_json())
