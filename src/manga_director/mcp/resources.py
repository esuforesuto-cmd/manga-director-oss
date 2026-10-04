"""Read-only MCP resources backed by the Application Service and repository port."""

from __future__ import annotations

import json
from collections.abc import Sequence
from urllib.parse import unquote

from manga_director.domain.exceptions import ValidationError
from manga_director.mcp.application import MangaApplicationService
from manga_director.mcp.contracts import McpResource, _validated_project_id


class McpResourceProvider:
    """Expose project data as safe read-only `manga://` JSON resources."""

    def __init__(self, service: MangaApplicationService) -> None:
        self._service = service

    def list(self) -> Sequence[McpResource]:
        return [
            McpResource(
                uri="manga://projects",
                name="Projects",
                description="All persisted manga projects.",
            ),
            McpResource(
                uri="manga://projects/{project_id}",
                name="Project",
                description="One persisted project aggregate.",
            ),
            McpResource(
                uri="manga://projects/{project_id}/status",
                name="Project status",
                description="Project workflow status.",
            ),
            McpResource(
                uri="manga://projects/{project_id}/chapters/{chapter_id}",
                name="Chapter",
                description="Chapter workflow status and page order.",
            ),
            McpResource(
                uri="manga://projects/{project_id}/chapters/{chapter_id}/pages/{page_number}",
                name="Page",
                description="One persisted page aggregate.",
            ),
            McpResource(
                uri="manga://projects/{project_id}/history",
                name="Project history",
                description="Project lifecycle and page workflow history.",
            ),
        ]

    def read(self, uri: str) -> dict[str, str]:
        """Resolve a supported resource URI into JSON text without changing state."""
        project_id, suffix = self._project_path(uri)
        if project_id is None:
            value = self._service.list_projects()
        elif suffix == []:
            value = self._service.get_project(project_id)
        elif suffix == ["status"]:
            project = self._service.get_project(project_id)
            value = {
                "project_id": project.id,
                "current_chapter": project.workflow.get("current_chapter"),
                "current_page": project.workflow.get("current_page"),
                "history": project.workflow.get("history", []),
            }
        elif suffix == ["history"]:
            project = self._service.get_project(project_id)
            value = {
                "project_history": project.workflow.get("history", []),
                "page_history": {str(page.page_number): page.history for page in project.pages},
            }
        elif len(suffix) == 2 and suffix[0] == "chapters":
            value = self._service.get_chapter_status(project_id, suffix[1])
        elif len(suffix) == 4 and suffix[0] == "chapters" and suffix[2] == "pages":
            value = self._service.get_project(project_id).page(int(suffix[3]))
        else:
            raise ValidationError(f"Unsupported MCP resource URI '{uri}'.")
        payload = value.model_dump(mode="json") if hasattr(value, "model_dump") else value
        return {"uri": uri, "mimeType": "application/json", "text": json.dumps(payload)}

    @staticmethod
    def _project_path(uri: str) -> tuple[str | None, Sequence[str]]:
        if uri == "manga://projects":
            return None, []
        prefix = "manga://projects/"
        if not uri.startswith(prefix):
            raise ValidationError(f"Unsupported MCP resource URI '{uri}'.")
        segments = [unquote(segment) for segment in uri[len(prefix) :].split("/") if segment]
        if not segments:
            raise ValidationError(f"Unsupported MCP resource URI '{uri}'.")
        try:
            project_id = _validated_project_id(segments[0])
        except ValueError as exc:
            raise ValidationError("MCP resource project_id is invalid.") from exc
        return project_id, segments[1:]
