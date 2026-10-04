"""Measure bounded repository-derived knowledge search."""

from time import perf_counter

from manga_director.production import KnowledgeService
from manga_director.repositories import InMemoryRepository


def run(iterations: int = 500) -> float:
    service = KnowledgeService(InMemoryRepository())
    started = perf_counter()
    for _ in range(iterations):
        service.search("project")
    return perf_counter() - started
