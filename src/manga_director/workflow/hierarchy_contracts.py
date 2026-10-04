"""Typed contexts and results for Project → Chapter → Page orchestration."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from manga_director.domain.events import WorkflowEvent
from manga_director.domain.project import Chapter, Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.workflow.contracts import WorkflowContext


class PageReadinessInspection(BaseModel):
    """Read-only persisted-evidence and next-operation view for one Page."""

    model_config = ConfigDict(frozen=True)

    page_number: int
    current_state: PageState
    unmet_prerequisites: tuple[str, ...] = ()
    next_operation: str
    non_execution: bool = True


class ProjectReadinessSummary(BaseModel):
    """Immutable aggregate of the existing read-only Page readiness inspections."""

    model_config = ConfigDict(frozen=True)

    completed_page_count: int
    actionable_page_count: int
    blocked_page_count: int
    next_actionable_page_number: int | None
    first_blocked_page: PageReadinessInspection | None = None
    next_actionable_page: PageReadinessInspection | None = None
    readiness_outcome: Literal["EMPTY", "ACTIONABLE", "BLOCKED", "COMPLETE"] | None = None
    readiness_focus_page: PageReadinessInspection | None = None


class ProjectContext(BaseModel):
    """Persistable Project-level workflow view with its current chapter/page position."""

    model_config = ConfigDict(frozen=True)

    project: Project
    chapters: list[Chapter] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    history: list[dict[str, Any]] = Field(default_factory=list)
    current_chapter: str | None = None
    current_page: int | None = None
    page_readiness: list[PageReadinessInspection] = Field(default_factory=list)
    readiness_summary: ProjectReadinessSummary | None = None


class ChapterContext(BaseModel):
    """Ordered Chapter-level workflow view over persisted page aggregates."""

    model_config = ConfigDict(frozen=True)

    chapter: Chapter
    pages: list[Page] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    history: list[dict[str, Any]] = Field(default_factory=list)
    current_page: int | None = None


class ChapterWorkflowResult(BaseModel):
    """Outcome of scheduling and executing at most one page in a chapter."""

    model_config = ConfigDict(frozen=True)

    context: ChapterContext
    page_context: WorkflowContext | None = None
    completed: bool
    events: list[WorkflowEvent] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)


class ProjectWorkflowResult(BaseModel):
    """Outcome of a Project-level operation with optional child execution detail."""

    model_config = ConfigDict(frozen=True)

    context: ProjectContext
    chapter_result: ChapterWorkflowResult | None = None
    events: list[WorkflowEvent] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)
