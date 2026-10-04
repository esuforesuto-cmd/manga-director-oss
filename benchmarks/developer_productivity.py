"""Measure template-descriptor construction without filesystem writes."""

from time import perf_counter

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.production import (
    CollaborationPlanningService,
    DirectorFoundationService,
    DirectorPlanningService,
    KnowledgeService,
    PlanningService,
    ProviderOrchestrator,
    V31FoundationService,
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository


def run(iterations: int = 500) -> float:
    repository = InMemoryRepository()
    planning = PlanningService(
        planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
    )
    foundation = DirectorPlanningService(
        DirectorFoundationService(planning, KnowledgeService(repository)), planning
    )
    service = V31FoundationService(foundation, CollaborationPlanningService(foundation), repository)
    started = perf_counter()
    for _ in range(iterations):
        service.developer_productivity_dashboard()
    return perf_counter() - started
