"""Render a production-quality summary without running a workflow or Provider."""

from pathlib import Path

from manga_director.cli.config import AppConfig
from manga_director.domain.project import Page, Project
from manga_director.production import QualityAutomation
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def main() -> None:
    repository = InMemoryRepository()
    repository.save(Project(id="production", title="Production", pages=[Page(page_number=1)]))
    quality = QualityAutomation(
        repository=repository,
        configuration=AppConfig(),
        root=Path(__file__).resolve().parents[2],
    )
    print(quality.production_summary(WorkflowContext(page={"id": "one"}), "production").to_markdown())


if __name__ == "__main__":
    main()
