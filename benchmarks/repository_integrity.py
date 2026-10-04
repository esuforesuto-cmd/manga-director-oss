"""Repository integrity self-check timing."""

from __future__ import annotations

from time import perf_counter

from manga_director.domain.project import Page, Project
from manga_director.repositories import InMemoryRepository, RepositorySelfCheck


def run() -> float:
    repository = InMemoryRepository()
    repository.save(Project(id="integrity", title="Integrity", pages=[Page(page_number=1)]))
    started = perf_counter()
    assert RepositorySelfCheck(repository).check("integrity").healthy is True
    return perf_counter() - started
