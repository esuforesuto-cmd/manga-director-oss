"""Contracts for the opt-in v6.1 Project and Workspace query scale service."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.production import (
    ProjectHubReferenceDTO,
    V60CreativeProductionPlatformFoundationService,
    V61ProjectWorkspaceQueryScaleService,
    WorkspaceHubReferenceDTO,
)

ROOT = Path(__file__).resolve().parents[1]


def _projects() -> tuple[ProjectHubReferenceDTO, ...]:
    return (
        ProjectHubReferenceDTO(project_id="project:three", title="Three"),
        ProjectHubReferenceDTO(project_id="project:one", title="One"),
        ProjectHubReferenceDTO(project_id="project:two", title="Two"),
    )


def _workspaces() -> tuple[WorkspaceHubReferenceDTO, ...]:
    return (
        WorkspaceHubReferenceDTO(
            workspace_id="workspace:three", project_id="project:three", label="Three"
        ),
        WorkspaceHubReferenceDTO(
            workspace_id="workspace:one", project_id="project:one", label="One"
        ),
        WorkspaceHubReferenceDTO(
            workspace_id="workspace:two", project_id="project:two", label="Two"
        ),
    )


def test_project_summary_page_reuses_hub_ordering_and_reports_window_boundaries() -> None:
    report = V61ProjectWorkspaceQueryScaleService().project_summary_page(
        _projects(), offset=1, limit=1
    )

    assert tuple(project.project_id for project in report.projects) == ("project:three",)
    assert report.window.offset == 1
    assert report.window.limit == 1
    assert report.window.total == 3
    assert report.window.has_next is True
    assert report.cross_project_workflow_executed is False
    assert report.repository_queried is False
    assert report.planning_only is True


def test_project_summary_page_uses_the_default_window_and_handles_final_and_empty_pages() -> None:
    service = V61ProjectWorkspaceQueryScaleService()
    projects = tuple(
        ProjectHubReferenceDTO(project_id=f"project:{index:02d}", title=str(index))
        for index in range(51)
    )

    first = service.project_summary_page(projects)
    final = service.project_summary_page(projects, offset=50, limit=50)
    beyond = service.project_summary_page(projects, offset=99, limit=50)
    empty = service.project_summary_page()

    assert len(first.projects) == 50
    assert first.window.has_next is True
    assert tuple(project.project_id for project in final.projects) == ("project:50",)
    assert final.window.has_next is False
    assert beyond.projects == ()
    assert beyond.window.total == 51
    assert beyond.window.has_next is False
    assert empty.projects == ()
    assert empty.window.total == 0
    assert empty.window.has_next is False


def test_workspace_summary_page_reuses_hub_ordering_and_reports_window_boundaries() -> None:
    report = V61ProjectWorkspaceQueryScaleService().workspace_summary_page(
        _workspaces(), offset=0, limit=2
    )

    assert tuple(workspace.workspace_id for workspace in report.workspaces) == (
        "workspace:one",
        "workspace:three",
    )
    assert report.window.total == 3
    assert report.window.has_next is True
    assert report.workspace_mutated is False
    assert report.repository_queried is False
    assert report.planning_only is True


@pytest.mark.parametrize("method_name, items", [("project_summary_page", _projects()), ("workspace_summary_page", _workspaces())])
@pytest.mark.parametrize(("offset", "limit", "message"), [(-1, 1, "offset"), (0, 0, "limit"), (0, -1, "limit")])
def test_summary_pages_reject_invalid_windows(
    method_name: str,
    items: tuple[ProjectHubReferenceDTO, ...] | tuple[WorkspaceHubReferenceDTO, ...],
    offset: int,
    limit: int,
    message: str,
) -> None:
    method = getattr(V61ProjectWorkspaceQueryScaleService(), method_name)

    with pytest.raises(ValueError, match=message):
        method(items, offset=offset, limit=limit)


def test_summary_pages_reuse_existing_duplicate_identifier_validation() -> None:
    service = V61ProjectWorkspaceQueryScaleService()

    with pytest.raises(ValueError, match="project_id values must be unique"):
        service.project_summary_page(
            (
                ProjectHubReferenceDTO(project_id="project:one", title="One"),
                ProjectHubReferenceDTO(project_id="project:one", title="Duplicate"),
            )
        )
    with pytest.raises(ValueError, match="workspace_id values must be unique"):
        service.workspace_summary_page(
            (
                WorkspaceHubReferenceDTO(
                    workspace_id="workspace:one", project_id="project:one", label="One"
                ),
                WorkspaceHubReferenceDTO(
                    workspace_id="workspace:one", project_id="project:two", label="Duplicate"
                ),
            )
        )


def test_summary_pages_preserve_input_and_returned_snapshot_immutability() -> None:
    projects = _projects()
    before = tuple(project.model_dump() for project in projects)
    report = V61ProjectWorkspaceQueryScaleService().project_summary_page(projects, limit=1)
    replacement = projects[0].model_copy(update={"title": "Changed"})

    assert tuple(project.model_dump() for project in projects) == before
    assert replacement.title == "Changed"
    assert report.projects[0].title == "One"
    with pytest.raises(ValidationError):
        report.window.offset = 1


def test_existing_hub_behavior_is_unchanged() -> None:
    report = V60CreativeProductionPlatformFoundationService().project_hub(_projects())

    assert tuple(project.project_id for project in report.projects) == (
        "project:one",
        "project:three",
        "project:two",
    )
    assert report.project_count == 3
    assert report.cross_project_workflow_executed is False


def test_query_scale_keeps_repository_delivery_and_execution_boundaries_out() -> None:
    source = (ROOT / "src/manga_director/production/v6_1_query_scale.py").read_text(
        encoding="utf-8"
    )

    for forbidden in (
        "manga_director.api",
        "manga_director.cli",
        "manga_director.mcp",
        "manga_director.repositories",
        "workflow.engine",
        ".execute(",
        ".advance(",
        "save(",
        ".publish(",
        ".load(",
    ):
        assert forbidden not in source
