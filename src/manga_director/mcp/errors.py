"""Expected-error mapping for MCP callers; stack traces remain in server logs only."""

from __future__ import annotations

from manga_director.domain.exceptions import (
    ConfigurationError,
    ImageGeneratorError,
    LLMProviderError,
    RepositoryError,
    StateTransitionError,
    ValidationError,
    WorkflowError,
)
from manga_director.mcp.contracts import McpToolResult


def map_error(operation: str, error: Exception) -> McpToolResult:
    """Return a safe structured error without exposing tracebacks or prompt content."""
    category = "internal_error"
    if isinstance(error, ValidationError):
        category = "validation_error"
    elif isinstance(error, StateTransitionError):
        category = "state_transition_error"
    elif isinstance(error, RepositoryError):
        category = "repository_error"
    elif isinstance(error, ConfigurationError):
        category = "configuration_error"
    elif isinstance(error, ImageGeneratorError):
        category = "image_generator_error"
    elif isinstance(error, LLMProviderError):
        category = "llm_error"
    elif isinstance(error, WorkflowError):
        category = "workflow_error"
    return McpToolResult(
        success=False,
        operation=operation,
        errors=[f"{category}: {error}"],
        metadata={"error_type": category},
    )
