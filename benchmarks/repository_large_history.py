"""Bounded large-history pagination smoke benchmark."""

from __future__ import annotations

from time import perf_counter

from manga_director.domain.project import Page, Project
from manga_director.repositories import InMemoryRepository, RepositoryScalability


def run(entries: int = 1_000) -> float:
    repository = InMemoryRepository()
    repository.save(
        Project(
            id="history-benchmark",
            title="History benchmark",
            pages=[Page(page_number=1, history=[{"sequence": index} for index in range(entries)])],
        )
    )
    scalability = RepositoryScalability(repository)
    start = perf_counter()
    for offset in range(0, entries, 50):
        scalability.history_page("history-benchmark", 1, offset=offset, limit=50)
    return perf_counter() - start


if __name__ == "__main__":
    print(f"repository_large_history: {run():.6f}s")
