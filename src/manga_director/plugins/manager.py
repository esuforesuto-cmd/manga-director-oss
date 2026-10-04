"""Plugin lifecycle orchestration, dependency ordering, and local administration."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from manga_director.domain.exceptions import (
    PluginDependencyError,
    PluginLifecycleError,
    PluginManifestError,
)
from manga_director.plugins.contracts import Plugin
from manga_director.plugins.discovery import DiscoveredPlugin, PluginDiscovery
from manga_director.plugins.loader import PluginLoader
from manga_director.plugins.manifest import PluginManifest
from manga_director.plugins.registry import PluginRegistry


@dataclass(frozen=True)
class PluginStatus:
    """Safe metadata shown by CLI and library callers."""

    name: str
    version: str
    description: str
    enabled: bool
    active: bool
    dependencies: tuple[str, ...]
    path: Path

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "enabled": self.enabled,
            "active": self.active,
            "dependencies": list(self.dependencies),
            "path": str(self.path),
        }


class PluginManager:
    """Coordinates local discovery, dependency resolution, and plugin lifecycle."""

    def __init__(
        self,
        plugins_directory: Path,
        registry: PluginRegistry | None = None,
        loader: PluginLoader | None = None,
    ) -> None:
        self._discovery = PluginDiscovery(plugins_directory)
        self._registry = registry or PluginRegistry()
        self._loader = loader or PluginLoader()
        self._active: dict[str, Plugin] = {}
        self._dependency_cache: dict[tuple[tuple[str, tuple[str, ...], bool], ...], tuple[str, ...]] = {}
        self._initialization_seconds: dict[str, float] = {}

    @property
    def registry(self) -> PluginRegistry:
        return self._registry

    def discover(self) -> list[DiscoveredPlugin]:
        """Discover manifests without importing any plugin code."""
        return self._discovery.discover()

    def statuses(self) -> list[PluginStatus]:
        """Return known plugin metadata without activating inactive plugins."""
        return [self._status(item) for item in self.discover()]

    def info(self, name: str) -> PluginStatus:
        """Return metadata for one discovered plugin."""
        return self._status(self._discovery.find(name))

    def load_enabled(self) -> list[Plugin]:
        """Initialize and register enabled plugins in dependency order."""
        discovered = {item.manifest.name: item for item in self.discover()}
        enabled = {name: item for name, item in discovered.items() if item.manifest.enabled}
        ordered = self._resolve_dependencies(enabled, discovered)
        return self._load_ordered(ordered)

    def load(self, name: str) -> list[Plugin]:
        """Lazily initialize one enabled plugin and its enabled dependencies."""

        discovered = {item.manifest.name: item for item in self.discover()}
        try:
            requested = discovered[name]
        except KeyError as exc:
            raise PluginManifestError(f"Plugin '{name}' was not found.") from exc
        if not requested.manifest.enabled:
            raise PluginDependencyError(f"Plugin '{name}' is disabled.")
        enabled = {plugin_name: item for plugin_name, item in discovered.items() if item.manifest.enabled}
        ordered = self._resolve_dependencies(enabled, discovered, targets=(name,))
        return self._load_ordered(ordered)

    def _load_ordered(self, ordered: list[DiscoveredPlugin]) -> list[Plugin]:
        loaded: list[Plugin] = []
        try:
            for item in ordered:
                if item.manifest.name in self._active:
                    continue
                plugin = self._loader.load(item)
                self._initialize_and_register(plugin)
                self._active[plugin.name] = plugin
                loaded.append(plugin)
        except PluginLifecycleError:
            for plugin in reversed(loaded):
                self._stop(plugin)
                self._active.pop(plugin.name, None)
            raise
        return loaded

    def shutdown(self) -> None:
        """Stop active plugins in reverse dependency/load order."""
        failures: list[str] = []
        for plugin in reversed(list(self._active.values())):
            try:
                self._stop(plugin)
            except PluginLifecycleError as exc:
                failures.append(str(exc))
        self._active.clear()
        if failures:
            raise PluginLifecycleError("; ".join(failures))

    def enable(self, name: str) -> PluginManifest:
        """Enable a manifest for the next process startup."""
        return self._discovery.set_enabled(name, True)

    def disable(self, name: str) -> PluginManifest:
        """Disable a manifest for the next process startup."""
        if name in self._active:
            raise PluginLifecycleError(
                f"Plugin '{name}' is active; call shutdown before disabling it."
            )
        return self._discovery.set_enabled(name, False)

    def install(self, source: Path) -> PluginStatus:
        """Copy a local plugin directory into the configured plugins directory.

        Remote installation is deliberately unsupported. The source must be a
        directory containing exactly one top-level ``plugin.yaml``.
        """
        manifest_path = source / "plugin.yaml"
        if not source.is_dir() or not manifest_path.is_file():
            raise PluginManifestError(
                f"Plugin source must be a directory containing plugin.yaml: {source}"
            )
        source_manifest = next(
            (
                item
                for item in PluginDiscovery(source).discover()
                if item.manifest_path.resolve() == manifest_path.resolve()
            ),
            None,
        )
        if source_manifest is None:
            raise PluginManifestError(f"Unable to discover plugin source manifest: {manifest_path}")
        destination = self._discovery.plugins_directory / source_manifest.manifest.name
        if destination.exists():
            raise PluginManifestError(
                f"Plugin '{source_manifest.manifest.name}' is already installed."
            )
        try:
            self._discovery.plugins_directory.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, destination)
        except OSError as exc:
            raise PluginManifestError(f"Unable to install plugin from '{source}': {exc}") from exc
        return self.info(source_manifest.manifest.name)

    def remove(self, name: str) -> None:
        """Remove one installed child-directory plugin after exact target validation."""
        discovered = self._discovery.find(name)
        root = self._discovery.plugins_directory.resolve()
        target = discovered.directory.resolve()
        if target.parent != root or target == root:
            raise PluginManifestError(
                "Only plugins installed in direct child directories can be removed."
            )
        if name in self._active:
            raise PluginLifecycleError(
                f"Plugin '{name}' is active; call shutdown before removing it."
            )
        try:
            shutil.rmtree(target)
        except OSError as exc:
            raise PluginManifestError(f"Unable to remove plugin '{name}': {exc}") from exc

    def _status(self, discovered: DiscoveredPlugin) -> PluginStatus:
        manifest = discovered.manifest
        return PluginStatus(
            name=manifest.name,
            version=manifest.version,
            description=manifest.description,
            enabled=manifest.enabled,
            active=manifest.name in self._active,
            dependencies=tuple(manifest.dependencies),
            path=discovered.directory,
        )

    def diagnostics(self) -> dict[str, object]:
        """Return lifecycle/cache data without causing plugin imports."""

        return {
            "active": sorted(self._active),
            "initialization_seconds": dict(self._initialization_seconds),
            "dependency_cache_entries": len(self._dependency_cache),
            "discovery": self._discovery.diagnostics(),
            "loader": self._loader.diagnostics(),
        }

    def _resolve_dependencies(
        self,
        enabled: dict[str, DiscoveredPlugin],
        discovered: dict[str, DiscoveredPlugin],
        *,
        targets: tuple[str, ...] | None = None,
    ) -> list[DiscoveredPlugin]:
        key = tuple(
            sorted(
                (name, tuple(item.manifest.dependencies), item.manifest.enabled)
                for name, item in discovered.items()
            )
        ) + (("__targets__", tuple(sorted(targets or enabled)), True),)
        cached = self._dependency_cache.get(key)
        if cached is not None:
            return [discovered[name] for name in cached]
        resolved: list[DiscoveredPlugin] = []
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visited:
                return
            if name in visiting:
                raise PluginDependencyError(f"Circular plugin dependency detected at '{name}'.")
            try:
                plugin = discovered[name]
            except KeyError as exc:
                raise PluginDependencyError(f"Plugin dependency '{name}' was not found.") from exc
            if name not in enabled:
                raise PluginDependencyError(f"Plugin dependency '{name}' is disabled.")
            visiting.add(name)
            for dependency in plugin.manifest.dependencies:
                visit(dependency)
            visiting.remove(name)
            visited.add(name)
            resolved.append(plugin)

        for name in sorted(targets or enabled):
            visit(name)
        self._dependency_cache[key] = tuple(item.manifest.name for item in resolved)
        return resolved

    def _initialize_and_register(self, plugin: Plugin) -> None:
        try:
            started = perf_counter()
            plugin.initialize()
            plugin.register(self._registry)
            self._initialization_seconds[plugin.name] = perf_counter() - started
        except Exception as exc:
            self._registry.unregister_plugin(plugin.name)
            try:
                plugin.shutdown()
            except Exception:
                pass
            raise PluginLifecycleError(
                f"Plugin '{plugin.name}' failed during initialize/register: {exc}"
            ) from exc

    def _stop(self, plugin: Plugin) -> None:
        self._registry.unregister_plugin(plugin.name)
        try:
            plugin.shutdown()
        except Exception as exc:
            raise PluginLifecycleError(
                f"Plugin '{plugin.name}' failed during shutdown: {exc}"
            ) from exc
