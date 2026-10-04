from pathlib import Path

import pytest

from manga_director.domain.exceptions import ProjectNotFoundError, ValidationError
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.repositories import InMemoryRepository, LocalFileRepository
from manga_director.repositories.serializer import ProjectSerializer
from manga_director.repositories.validator import ProjectValidator


def _designed_project() -> Project:
    return Project(
        id="demo",
        title="Demo Manga",
        pages=[Page(page_number=1, state=PageState.DESIGNED, page_design={"purpose": "hook"})],
        characters=[{"name": "Aki"}],
    )


def test_in_memory_repository_supports_full_project_lifecycle() -> None:
    repository = InMemoryRepository()
    project = _designed_project()

    repository.save(project)

    assert repository.exists("demo") is True
    assert repository.load("demo") == project
    assert repository.list() == [project]
    repository.delete("demo")
    assert repository.exists("demo") is False
    with pytest.raises(ProjectNotFoundError):
        repository.load("demo")


@pytest.mark.parametrize("format", ["json", "yaml"])
def test_local_file_repository_persists_under_projects_directory(
    tmp_path: Path, format: str
) -> None:
    repository = LocalFileRepository(tmp_path, format=format)  # type: ignore[arg-type]
    project = _designed_project()

    repository.save(project)

    assert (tmp_path / "projects").exists()
    assert repository.load("demo") == project
    assert repository.list() == [project]


@pytest.mark.parametrize("format", ["json", "yaml"])
def test_serializer_round_trips_project(format: str) -> None:
    serializer = ProjectSerializer(format=format)  # type: ignore[arg-type]
    project = _designed_project()

    assert serializer.loads(serializer.dumps(project)) == project


def test_validator_rejects_state_without_required_artifact() -> None:
    invalid = Project(
        id="demo", title="Demo", pages=[Page(page_number=1, state=PageState.GENERATED)]
    )

    with pytest.raises(ValidationError, match="page_design"):
        ProjectValidator().validate(invalid)


def test_validator_rejects_duplicate_page_numbers() -> None:
    invalid = Project(id="demo", title="Demo", pages=[Page(page_number=1), Page(page_number=1)])

    with pytest.raises(ValidationError, match="unique"):
        ProjectValidator().validate(invalid)
