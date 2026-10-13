"""Backward-compatible MCP import for the shared workflow application service."""

from manga_director.application.workflow import WorkflowApplicationService

MangaApplicationService = WorkflowApplicationService

__all__ = ["MangaApplicationService"]
