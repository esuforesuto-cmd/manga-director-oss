"""Repository-backed bounded health-history timing."""

from __future__ import annotations

from time import perf_counter

from manga_director.domain.project import Page, Project
from manga_director.production import HealthHistoryStore
from manga_director.repositories import InMemoryRepository


def run() -> float:
    repository = InMemoryRepository()
    repository.save(Project(id="history", title="History", pages=[Page(page_number=1)]))
    history = HealthHistoryStore(repository)
    started = perf_counter()
    history.record("history", "runtime", True, {"mode": "local"})
    assert len(history.timeline("history").snapshots) == 1
    return perf_counter() - started
