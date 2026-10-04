"""Transport-neutral DTOs and validated input contracts for the local MCP server."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class McpToolResult(BaseModel):
    """Uniform, domain-model-free result returned by every MCP tool."""

    model_config = ConfigDict(frozen=True)

    success: bool
    operation: str
    state: str | None = None
    data: Any = None
    messages: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class McpInput(BaseModel):
    """Strict JSON input base: unsupported fields are rejected before tool dispatch."""

    model_config = ConfigDict(extra="forbid")


class CreateProjectInput(McpInput):
    project_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    page_number: int = Field(default=1, ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("project_id")
    @classmethod
    def _project_id_is_safe(cls, value: str) -> str:
        return _validated_project_id(value)


class EmptyInput(McpInput):
    """Explicit empty schema for tools that require no arguments."""


class ProjectInput(McpInput):
    project_id: str = Field(min_length=1)

    @field_validator("project_id")
    @classmethod
    def _project_id_is_safe(cls, value: str) -> str:
        return _validated_project_id(value)


class ChapterInput(ProjectInput):
    chapter_id: str = Field(min_length=1)


class PageInput(ProjectInput):
    page_number: int = Field(ge=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovePageInput(PageInput):
    approved_by: str = Field(min_length=1)


class PromptArguments(McpInput):
    arguments: dict[str, str] = Field(default_factory=dict)


class McpResource(BaseModel):
    model_config = ConfigDict(frozen=True, populate_by_name=True)

    uri: str
    name: str
    description: str
    mime_type: str = Field(default="application/json", alias="mimeType")


class McpPrompt(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    arguments: list[str] = Field(default_factory=list)


def _validated_project_id(value: str) -> str:
    """Apply the persisted project-ID contract before MCP dispatch."""

    if (
        not isinstance(value, str)
        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", value) is None
    ):
        raise ValueError("project_id must be a safe project identifier")
    return value
