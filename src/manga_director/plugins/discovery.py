"""Filesystem discovery and manifest state changes for local plugins."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from manga_director.domain.exceptions import PluginManifestError
from manga_director.plugins.manifest import PluginManifest


@dataclass(frozen=True)
class DiscoveredPlugin:
    """A plugin manifest and the directory containing its local code."""

    manifest: PluginManifest
    directory: Path
    manifest_path: Path


class PluginDiscovery:
    """Discovers direct child plugin directories under a configured plugins root."""

    def __init__(self, plugins_directory: Path) -> None:
        self._plugins_directory = plugins_directory
        self._discovery_stamp: tuple[tuple[str, int, int], ...] | None = None
        self._discovered: tuple[DiscoveredPlugin, ...] = ()
        self._manifest_cache: dict[Path, tuple[tuple[int, int], DiscoveredPlugin]] = {}

    @property
    def plugins_directory(self) -> Path:
        return self._plugins_directory

    def discover(self) -> list[DiscoveredPlugin]:
        """Read every direct child ``plugin.yaml`` in deterministic order."""
        if not self._plugins_directory.exists():
            return []
        if not self._plugins_directory.is_dir():
            raise PluginManifestError(f"Plugin path is not a directory: {self._plugins_directory}")

        paths = self._manifest_paths()
        stamp = tuple(
            (str(path.resolve()), path.stat().st_mtime_ns, path.stat().st_size) for path in paths
        )
        if stamp == self._discovery_stamp:
            return list(self._discovered)
        found = [self._read(path) for path in paths]
        names = [item.manifest.name for item in found]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise PluginManifestError(f"Duplicate plugin manifests: {', '.join(duplicates)}")
        self._discovery_stamp = stamp
        self._discovered = tuple(sorted(found, key=lambda item: item.manifest.name))
        return list(self._discovered)

    def find(self, name: str) -> DiscoveredPlugin:
        """Find one discovered plugin by its manifest name."""
        for plugin in self.discover():
            if plugin.manifest.name == name:
                return plugin
        raise PluginManifestError(f"Plugin '{name}' was not found in '{self._plugins_directory}'.")

    def set_enabled(self, name: str, enabled: bool) -> PluginManifest:
        """Persist only the manifest's enabled flag without loading plugin code."""
        discovered = self.find(name)
        raw = self._read_raw(discovered.manifest_path)
        raw["enabled"] = enabled
        try:
            serialized = yaml.safe_dump(raw, sort_keys=False, allow_unicode=True)
            discovered.manifest_path.write_text(serialized, encoding="utf-8")
        except OSError as exc:
            raise PluginManifestError(
                f"Unable to update plugin manifest '{discovered.manifest_path}': {exc}"
            ) from exc
        self.invalidate()
        return self._read(discovered.manifest_path).manifest

    def invalidate(self) -> None:
        """Forget cached manifests; useful after an external plugin deployment."""

        self._discovery_stamp = None
        self._discovered = ()
        self._manifest_cache.clear()

    def diagnostics(self) -> dict[str, object]:
        """Return cache state without importing any plugin code."""

        return {
            "directory": str(self._plugins_directory),
            "discovered": len(self._discovered),
            "manifest_cache_entries": len(self._manifest_cache),
            "cache_active": self._discovery_stamp is not None,
        }

    def _manifest_paths(self) -> list[Path]:
        root_manifest = self._plugins_directory / "plugin.yaml"
        paths = [root_manifest] if root_manifest.exists() else []
        paths.extend(
            sorted(self._plugins_directory.glob("*/plugin.yaml"), key=lambda item: str(item).lower())
        )
        return paths

    def _read(self, manifest_path: Path) -> DiscoveredPlugin:
        resolved = manifest_path.resolve()
        stamp = (manifest_path.stat().st_mtime_ns, manifest_path.stat().st_size)
        cached = self._manifest_cache.get(resolved)
        if cached is not None and cached[0] == stamp:
            return cached[1]
        raw = self._read_raw(manifest_path)
        discovered = DiscoveredPlugin(
            manifest=PluginManifest.from_mapping(raw, str(manifest_path)),
            directory=manifest_path.parent,
            manifest_path=manifest_path,
        )
        self._manifest_cache[resolved] = (stamp, discovered)
        return discovered

    @staticmethod
    def _read_raw(manifest_path: Path) -> dict[str, Any]:
        try:
            raw: Any = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise PluginManifestError(
                f"Unable to read plugin manifest '{manifest_path}': {exc}"
            ) from exc
        if not isinstance(raw, dict):
            raise PluginManifestError(
                f"Invalid plugin manifest '{manifest_path}': manifest root must be a mapping"
            )
        return raw
