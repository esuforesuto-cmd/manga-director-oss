"""Public surface of the Extension SDK."""

from manga_director.sdk.context import ExtensionContext
from manga_director.sdk.extension import (
    AgentExtension,
    CLIExtension,
    Extension,
    FastAPIExtension,
    ImageGeneratorExtension,
    LLMExtension,
    MCPToolExtension,
    NotificationExtension,
    PromptExtension,
    RepositoryExtension,
    WorkflowExtension,
)
from manga_director.sdk.loader import ExtensionLoader
from manga_director.sdk.manifest import ExtensionManifest, ExtensionValidator

__all__ = [
    "AgentExtension",
    "CLIExtension",
    "Extension",
    "ExtensionContext",
    "ExtensionLoader",
    "ExtensionManifest",
    "ExtensionValidator",
    "FastAPIExtension",
    "ImageGeneratorExtension",
    "LLMExtension",
    "MCPToolExtension",
    "NotificationExtension",
    "PromptExtension",
    "RepositoryExtension",
    "WorkflowExtension",
]
