"""Stable base classes for extension categories."""

from __future__ import annotations

from manga_director.sdk.context import ExtensionContext


class Extension:
    """Optional lifecycle hooks shared by every SDK extension."""

    def initialize(self, context: ExtensionContext) -> None:
        """Initialize the extension after validation and loading."""

        del context

    def shutdown(self) -> None:
        """Release extension-owned resources during application shutdown."""


class AgentExtension(Extension):
    """Marker base class for agent extensions."""


class WorkflowExtension(Extension):
    """Marker base class for workflow extensions."""


class RepositoryExtension(Extension):
    """Marker base class for repository extensions."""


class ImageGeneratorExtension(Extension):
    """Marker base class for image generator extensions."""


class LLMExtension(Extension):
    """Marker base class for LLM extensions."""


class PromptExtension(Extension):
    """Marker base class for prompt extensions."""


class NotificationExtension(Extension):
    """Marker base class for notification extensions."""


class CLIExtension(Extension):
    """Marker base class for CLI extensions."""


class FastAPIExtension(Extension):
    """Marker base class for FastAPI extensions."""


class MCPToolExtension(Extension):
    """Marker base class for MCP tool extensions."""
