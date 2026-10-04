"""Local plugin extension API for manga-director."""

from manga_director.plugins.composition import (
    apply_agent_plugins,
    apply_image_generator_plugins,
    apply_llm_plugins,
)
from manga_director.plugins.contracts import Plugin, PluginType
from manga_director.plugins.discovery import DiscoveredPlugin, PluginDiscovery
from manga_director.plugins.loader import PluginLoader
from manga_director.plugins.manager import PluginManager, PluginStatus
from manga_director.plugins.manifest import PluginManifest
from manga_director.plugins.registry import PluginContribution, PluginRegistry

__all__ = [
    "DiscoveredPlugin",
    "apply_agent_plugins",
    "apply_image_generator_plugins",
    "apply_llm_plugins",
    "Plugin",
    "PluginContribution",
    "PluginDiscovery",
    "PluginLoader",
    "PluginManager",
    "PluginManifest",
    "PluginRegistry",
    "PluginStatus",
    "PluginType",
]
