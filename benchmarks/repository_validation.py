"""Measure read-only repository maintenance validation with an in-memory fixture."""

from __future__ import annotations

from time import perf_counter

from manga_director.domain.project import Page, Project
from manga_director.production import RepositoryMaintenance
from manga_director.repositories import InMemoryRepository


def run(iterations: int = 100) -> float:
    repository = InMemoryRepository()
    repository.save(Project(id="benchmark", title="Benchmark", pages=[Page(page_number=1)]))
    maintenance = RepositoryMaintenance(repository)
    started = perf_counter()
    for _ in range(iterations):
        assert maintenance.report("benchmark").healthy
    return perf_counter() - started


if __name__ == "__main__":
    print(f"repository_validation: {run():.6f}s")
