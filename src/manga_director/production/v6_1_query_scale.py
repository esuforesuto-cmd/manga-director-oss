"""Read-only v6.1 pagination for caller-supplied Project and Workspace references.

The service reuses the v6.0 Hub validation and identifier ordering before
returning an immutable window.  It does not load repositories, persist data,
execute workflows, or bypass the StateMachine.
"""

from __future__ import annotations

from typing import Literal, TypeVar

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.production.v6_0_foundation import (
    ProjectHubReferenceDTO,
    V60CreativeProductionPlatformFoundationService,
    WorkspaceHubReferenceDTO,
)


class PaginationWindowDTO(DirectorModel):
    """Metadata for a deterministic, caller-supplied result window."""

    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1)
    total: int = Field(ge=0)
    has_next: bool


class ProjectHubPageReport(DirectorModel):
    projects: tuple[ProjectHubReferenceDTO, ...] = ()
    window: PaginationWindowDTO
    cross_project_workflow_executed: Literal[False] = False
    repository_queried: Literal[False] = False
    planning_only: Literal[True] = True


class WorkspaceHubPageReport(DirectorModel):
    workspaces: tuple[WorkspaceHubReferenceDTO, ...] = ()
    window: PaginationWindowDTO
    workspace_mutated: Literal[False] = False
    repository_queried: Literal[False] = False
    planning_only: Literal[True] = True


class V61ProjectWorkspaceQueryScaleService:
    """Create opt-in pagination reports without altering v6.0 Hub behavior."""

    def __init__(self) -> None:
        self._foundation = V60CreativeProductionPlatformFoundationService()

    def project_summary_page(
        self,
        projects: tuple[ProjectHubReferenceDTO, ...] = (),
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> ProjectHubPageReport:
        """Page the v6.0 Project Hub's validated, identifier-sorted snapshot."""

        snapshot = self._foundation.project_hub(projects).projects
        items, window = _window(snapshot, offset=offset, limit=limit)
        return ProjectHubPageReport(projects=items, window=window)

    def workspace_summary_page(
        self,
        workspaces: tuple[WorkspaceHubReferenceDTO, ...] = (),
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> WorkspaceHubPageReport:
        """Page the v6.0 Workspace Hub's validated, identifier-sorted snapshot."""

        snapshot = self._foundation.workspace_hub(workspaces).workspaces
        items, window = _window(snapshot, offset=offset, limit=limit)
        return WorkspaceHubPageReport(workspaces=items, window=window)


_Item = TypeVar("_Item")


def _window(
    items: tuple[_Item, ...], *, offset: int, limit: int
) -> tuple[tuple[_Item, ...], PaginationWindowDTO]:
    if offset < 0:
        raise ValueError("offset must be non-negative")
    if limit < 1:
        raise ValueError("limit must be at least 1")

    total = len(items)
    return (
        items[offset : offset + limit],
        PaginationWindowDTO(
            offset=offset,
            limit=limit,
            total=total,
            has_next=offset + limit < total,
        ),
    )
