"""Render a provider-free quality pipeline DTO for one persisted Page."""

from pathlib import Path

from manga_director.cli.config import AppConfig
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production import QualityAutomation
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def main() -> None:
    repository = InMemoryRepository()
    repository.save(Project(id="quality", title="Quality", pages=[Page(page_number=1)]))
    automation = QualityAutomation(
        repository=repository,
        configuration=AppConfig(),
        root=Path(__file__).resolve().parents[2],
    )
    context = WorkflowContext(
        page={"id": "one"},
        state=PageState.GENERATED,
        artifacts={PageState.STORYBOARDED.value: {"panels": []}},
    )
    print(automation.pipeline(context, "quality").to_markdown())


if __name__ == "__main__":
    main()
