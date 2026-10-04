"""Measure Creative Review DTO construction without review execution."""

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
    service = V31InsightsService(foundation, repository)
    context = WorkflowContext(page={"id": "benchmark-page"})
    started = perf_counter()
    for _ in range(iterations):
        service.creative_review_dashboard(context)
    return perf_counter() - started
