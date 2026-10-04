"""Smoke benchmark for local release-readiness report generation."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

from manga_director.cli.config import AppConfig
from manga_director.domain.project import Page, Project
from manga_director.production import QualityAutomation, ReleaseReadiness, RepositoryMaintenance
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def _service() -> ReleaseReadiness:
    root = Path(__file__).resolve().parents[1]
    repository = InMemoryRepository()
    repository.save(Project(id="benchmark", title="Benchmark", pages=[Page(page_number=1)]))
    return ReleaseReadiness(
        quality=QualityAutomation(repository=repository, configuration=AppConfig(), root=root),
        maintenance=RepositoryMaintenance(repository),
        root=root,
    )


def run() -> float:
    service = _service()
    started = perf_counter()
    service.release_readiness_report(WorkflowContext(page={"id": "one"}), "benchmark")
    return perf_counter() - started


if __name__ == "__main__":
    print(f"release_validation_seconds={run():.6f}")
