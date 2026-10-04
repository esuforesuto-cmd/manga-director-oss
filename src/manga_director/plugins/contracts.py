"""Typed plugin contracts. Plugin discovery is kept outside the workflow core."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Protocol, runtime_checkable


class PluginType(StrEnum):
    """Extension point categories supported by the plugin registry."""

    AGENT = "agent"
    WORKFLOW = "workflow"
    REPOSITORY = "repository"
    IMAGE_GENERATOR = "image_generator"
    LLM = "llm"
    PROMPT = "prompt"
    CLI = "cli"
    EVENT_BUS = "event_bus"


@runtime_checkable
class Plugin(Protocol):
    """Minimum lifecycle contract implemented by every local plugin."""

    name: str
    version: str
    description: str

    def initialize(self) -> None:
        """Prepare the plugin before it contributes any extension."""

    def register(self, registry: PluginRegistry) -> None:
        """Contribute typed capabilities to the provided registry."""

    def shutdown(self) -> None:
        """Release resources after the plugin is no longer in use."""


if TYPE_CHECKING:
    from manga_director.plugins.registry import PluginRegistry
