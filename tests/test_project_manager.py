"""Focused Project Manager contracts for Epic-001 / Issue-001."""

from __future__ import annotations

from manga_director.domain.project import Chapter, Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production import ProjectManagerService


class ReadOnlyProjectSource:
    """Minimal repository-port double that detects unexpected persistence."""

    def __init__(self, project: Project) -> None:
        self.project = project
        self.load_count = 0
        self.save_count = 0

    def load(self, project_id: str) -> Project:
        assert project_id == self.project.id
        self.load_count += 1
        return self.project.model_copy(deep=True)

    def save(self, project: Project) -> None:
        self.save_count += 1
        raise AssertionError("Project Manager inspection must not persist a project")

    def exists(self, project_id: str) -> bool:
        return project_id == self.project.id

    def delete(self, project_id: str) -> None:
        raise AssertionError("Project Manager inspection must not delete a project")


def _quality_checked_page(page_number: int) -> Page:
    return Page(
        page_number=page_number,
        state=PageState.QUALITY_CHECKED,
        page_design={},
        review={},
        storyboard={"panels": []},
        prompt={},
        image={},
        quality={"status": "passed"},
    )


def test_project_manager_inspects_one_active_page_without_persistence() -> None:
    source = ReadOnlyProjectSource(
        Project(
            id="volume-1",
            title="Volume One",
            chapters=[Chapter(id="chapter-1", title="Chapter 1", page_numbers=[1, 2])],
            pages=[Page(page_number=1), _quality_checked_page(2)],
            workflow={"current_chapter": "chapter-1", "current_page": 2},
        )
    )

    report = ProjectManagerService(source).inspect("volume-1")

    assert report.project_id == "volume-1"
    assert report.current_chapter_id == "chapter-1"
    assert report.active_page is not None
    assert report.active_page.page_number == 2
    assert report.active_page.storyboard_persisted is True
    assert report.active_page.quality_review_completed is True
    assert report.summary.page_count == 2
    assert report.summary.approved_page_count == 0
    assert report.summary.repository_mutated is False
    assert report.state_machine_authoritative is True
    assert source.load_count == 1
    assert source.save_count == 0


def test_project_manager_selects_first_incomplete_page_and_requires_storyboard() -> None:
    source = ReadOnlyProjectSource(
        Project(
            id="volume-2",
            title="Volume Two",
            chapters=[Chapter(id="chapter-1", title="Chapter 1", page_numbers=[1])],
            pages=[Page(page_number=1)],
        )
    )

    report = ProjectManagerService(source).inspect("volume-2")

    assert report.active_page is not None
    assert report.active_page.page_number == 1
    assert report.current_chapter_id == "chapter-1"
    assert "storyboard" in report.recommendation.lower()
    assert report.summary.workflow_executed is False


def test_project_manager_reports_completed_project_without_selecting_a_page() -> None:
    source = ReadOnlyProjectSource(
        Project(
            id="volume-3",
            title="Volume Three",
            chapters=[Chapter(id="chapter-1", title="Chapter 1", page_numbers=[1])],
            pages=[
                Page(
                    page_number=1,
                    state=PageState.APPROVED,
                    page_design={},
                    review={},
                    storyboard={},
                    prompt={},
                    image={},
                    quality={},
                    approval={},
                )
            ],
        )
    )

    report = ProjectManagerService(source).inspect("volume-3")

    assert report.active_page is None
    assert report.summary.project_completed is True
    assert report.summary.approved_page_count == 1
    assert "no workflow action" in report.recommendation.lower()
