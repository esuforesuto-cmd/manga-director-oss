"""Measure redacted Knowledge Analytics DTO construction."""

from time import perf_counter

from manga_director.adapters.runtime import LLMProviderRuntime
from manga_director.domain.project import Page, Project
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


def run(iterations: int = 500) -> float:
    repository = InMemoryRepository()
    repository.save(Project(id="benchmark", title="Benchmark", pages=[Page(page_number=1)]))
    planning = PlanningService(
        planner=WorkflowPlanner(), providers=ProviderOrchestrator(LLMProviderRuntime())
    )
    director = DirectorPlanningService(
        DirectorFoundationService(planning, KnowledgeService(repository)), planning
    )
    foundation = V31FoundationService(director, CollaborationPlanningService(director), repository)
    service = V31InsightsService(foundation, repository)
    started = perf_counter()
    for _ in range(iterations):
        service.knowledge_analytics_dashboard()
    return perf_counter() - started
