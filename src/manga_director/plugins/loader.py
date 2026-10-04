"""Imports plugin entry points after manifest discovery has completed."""

from __future__ import annotations

import importlib
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import cast

from manga_director.domain.exceptions import PluginLifecycleError
from manga_director.plugins.contracts import Plugin
from manga_director.plugins.discovery import DiscoveredPlugin


class PluginLoader:
    """Loads a local plugin class from the manifest's ``module:attribute`` entry point."""

    def __init__(self) -> None:
        self._factories: dict[tuple[str, int, str], Callable[[], Plugin]] = {}

    def load(self, discovered: DiscoveredPlugin) -> Plugin:
        module_name, _, attribute_name = discovered.manifest.entry_point.partition(":")
        try:
            factory = self._factory(discovered, module_name, attribute_name)
            plugin = factory()
        except (AttributeError, ImportError, OSError, TypeError, ValueError) as exc:
            raise PluginLifecycleError(
                f"Unable to load plugin '{discovered.manifest.name}' from "
                f"'{discovered.manifest.entry_point}': {exc}"
            ) from exc

        if not isinstance(plugin, Plugin):
            raise PluginLifecycleError(
                f"Plugin '{discovered.manifest.name}' does not implement the Plugin lifecycle contract."
            )
        self._validate_identity(discovered, plugin)
        return plugin

    def diagnostics(self) -> dict[str, object]:
        return {"factory_cache_entries": len(self._factories)}

    def _factory(
        self, discovered: DiscoveredPlugin, module_name: str, attribute_name: str
    ) -> Callable[[], Plugin]:
        key = (
            str(discovered.manifest_path.resolve()),
            discovered.manifest_path.stat().st_mtime_ns,
            discovered.manifest.entry_point,
        )
        cached = self._factories.get(key)
        if cached is not None:
            return cached
        with self._plugin_path(discovered.directory):
            module = importlib.import_module(module_name)
        factory = getattr(module, attribute_name)
        if not callable(factory):
            raise TypeError(f"Plugin factory '{discovered.manifest.entry_point}' is not callable")
        typed_factory = cast(Callable[[], Plugin], factory)
        self._factories[key] = typed_factory
        return typed_factory

    @staticmethod
    def _validate_identity(discovered: DiscoveredPlugin, plugin: Plugin) -> None:
        if plugin.name != discovered.manifest.name:
            raise PluginLifecycleError(
                f"Plugin entry point name '{plugin.name}' does not match manifest name "
                f"'{discovered.manifest.name}'."
            )
        if plugin.version != discovered.manifest.version:
            raise PluginLifecycleError(
                f"Plugin '{plugin.name}' version '{plugin.version}' does not match manifest version "
                f"'{discovered.manifest.version}'."
            )

    @staticmethod
    @contextmanager
    def _plugin_path(directory: Path) -> Iterator[None]:
        path = str(directory)
        sys.path.insert(0, path)
        try:
            yield
        finally:
            try:
                sys.path.remove(path)
            except ValueError:
                pass
