"""Measure readiness DTO composition without deployment or probing."""

from time import perf_counter

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.production import (
    CollaborationPlanningService,
    DirectorFoundationService,
    DirectorPlanningService,
    KnowledgeService,
    PlanningService,
    ProviderOrchestrator,
    V31AssuranceService,
    V31FoundationService,
    V31InsightsService,
    WorkflowPlanner,
)
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def run(iterations: int = 500) -> float:
    repository = InMemoryRepository()
    planning = PlanningService(
        planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
    )
    director = DirectorPlanningService(
        DirectorFoundationService(planning, KnowledgeService(repository)), planning
    )
    foundation = V31FoundationService(director, CollaborationPlanningService(director), repository)
    service = V31AssuranceService(foundation, V31InsightsService(foundation, repository), repository)
    context = WorkflowContext(page={"id": "benchmark-page"})
    started = perf_counter()
    for _ in range(iterations):
        service.operational_readiness_dashboard(context, {"mode": "testing"})
    return perf_counter() - started
