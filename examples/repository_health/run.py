"""Inspect repository health without mutating stored Projects."""

from pathlib import Path

from manga_director.cli.config import AppConfig
from manga_director.domain.project import Page, Project
from manga_director.production import QualityAutomation, ReleaseReadiness, RepositoryMaintenance
from manga_director.repositories import InMemoryRepository


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    repository = InMemoryRepository()
    repository.save(Project(id="health", title="Health", pages=[Page(page_number=1)]))
    service = ReleaseReadiness(
        quality=QualityAutomation(repository=repository, configuration=AppConfig(), root=root),
        maintenance=RepositoryMaintenance(repository),
        root=root,
    )
    print(service.repository_health_report("health").to_markdown())


if __name__ == "__main__":
    main()
