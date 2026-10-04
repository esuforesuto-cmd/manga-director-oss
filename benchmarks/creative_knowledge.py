"""Measure v3 Creative Knowledge DTO construction without repository writes."""

from time import perf_counter

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


def run(iterations: int = 500) -> float:
    planning = PlanningService(planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime()))
    platform = DirectorPlanningService(DirectorFoundationService(planning, KnowledgeService(InMemoryRepository())), planning)
    service = CollaborationPlanningService(platform)
    started = perf_counter()
    for _ in range(iterations):
        service.creative_knowledge()
    return perf_counter() - started
