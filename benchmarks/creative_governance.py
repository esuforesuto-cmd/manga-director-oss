"""Measure v3 Creative Governance DTO composition without mutation."""

from time import perf_counter

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


def run(iterations: int = 500) -> float:
    planning = PlanningService(planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime()))
    foundation = DirectorPlanningService(DirectorFoundationService(planning, KnowledgeService(InMemoryRepository())), planning)
    service = V3ReadinessService(foundation, CollaborationPlanningService(foundation))
    started = perf_counter()
    for _ in range(iterations):
        service.creative_governance(WorkflowContext())
    return perf_counter() - started
