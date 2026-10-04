"""Read-only Project Manager inspection for the Production Core.

The service reads an existing Project aggregate through the established
``ProjectRepository`` port. It never saves, transitions, schedules, or
approves a Page; the domain StateMachine remains the transition authority.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.repositories.protocols import ProjectRepository


class ActiveProjectPageDTO(DirectorModel):
    """The single Page selected for read-only project-status inspection."""

    page_number: int = Field(ge=1)
    state: PageState
    storyboard_persisted: bool
    quality_review_completed: bool
    approval_recorded: bool


class ProjectManagementSummary(DirectorModel):
    chapter_count: int = Field(ge=0)
    page_count: int = Field(ge=0)
    approved_page_count: int = Field(ge=0)
    remaining_page_count: int = Field(ge=0)
    project_completed: bool
    workflow_executed: Literal[False] = False
    repository_mutated: Literal[False] = False


class ProjectManagementReport(DirectorModel):
    project_id: str
    title: str
    current_chapter_id: str | None = None
    active_page: ActiveProjectPageDTO | None = None
    summary: ProjectManagementSummary
    recommendation: str
    state_machine_authoritative: Literal[True] = True
    planning_only: Literal[True] = True


class ProjectManagerService:
    """Project-scoped, repository-port-only status inspection.

    This is deliberately separate from ``ProjectWorkflowEngine``: that engine
    owns lifecycle changes, while this service only projects persisted state.
    """

    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository

    def inspect(self, project_id: str) -> ProjectManagementReport:
        """Return a compact report without changing the project or its workflow."""
        project = self._repository.load(project_id)
        active_page = _active_page(project)
        approved_page_count = sum(page.state is PageState.APPROVED for page in project.pages)
        page_count = len(project.pages)
        completed = bool(project.pages) and approved_page_count == page_count
        return ProjectManagementReport(
            project_id=project.id,
            title=project.title,
            current_chapter_id=_current_chapter_id(project, active_page),
            active_page=None if active_page is None else _active_page_dto(active_page),
            summary=ProjectManagementSummary(
                chapter_count=len(project.chapters),
                page_count=page_count,
                approved_page_count=approved_page_count,
                remaining_page_count=page_count - approved_page_count,
                project_completed=completed,
            ),
            recommendation=_recommendation(active_page, completed),
        )


def _active_page(project: Project) -> Page | None:
    current_page = project.workflow.get("current_page")
    if isinstance(current_page, int) and not isinstance(current_page, bool):
        for page in project.pages:
            if page.page_number == current_page:
                return page
    return next(
        (page for page in sorted(project.pages, key=lambda item: item.page_number) if page.state is not PageState.APPROVED),
        None,
    )


def _current_chapter_id(project: Project, active_page: Page | None) -> str | None:
    current_chapter = project.workflow.get("current_chapter")
    if isinstance(current_chapter, str):
        return current_chapter
    if active_page is None:
        return None
    return next(
        (
            chapter.id
            for chapter in project.chapters
            if active_page.page_number in chapter.page_numbers
        ),
        None,
    )


def _active_page_dto(page: Page) -> ActiveProjectPageDTO:
    return ActiveProjectPageDTO(
        page_number=page.page_number,
        state=page.state,
        storyboard_persisted=page.storyboard is not None,
        quality_review_completed=(
            page.state in (PageState.QUALITY_CHECKED, PageState.APPROVED) and page.quality is not None
        ),
        approval_recorded=page.approval is not None,
    )


def _recommendation(active_page: Page | None, completed: bool) -> str:
    if completed:
        return "All Pages are approved; no workflow action is requested."
    if active_page is None:
        return "No active Page is available; use the existing Project Workflow to establish progress."
    if active_page.storyboard is None:
        return "Persist a storyboard through the existing workflow before image generation."
    if active_page.quality is None:
        return "Complete quality review through the existing workflow before approval."
    return "Use the existing StateMachine-authorized workflow for the next Page step."
