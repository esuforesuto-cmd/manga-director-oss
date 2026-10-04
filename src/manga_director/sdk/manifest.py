"""Manifest model and validation for SDK extension packages."""

from __future__ import annotations

import re
from importlib import import_module
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from manga_director._version import __version__
from manga_director.domain.exceptions import ValidationError

SDK_VERSION = "1.0"
_VERSION_PATTERN = re.compile(r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:(a|b|rc)(\d+))?$")


class ExtensionManifest(BaseModel):
    """Portable metadata required by an SDK extension package."""

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str
    version: str
    author: str
    license: str
    description: str
    entry_point: str
    dependencies: list[str] = Field(default_factory=list)
    minimum_core_version: str = "1.0.0"
    enabled: bool = True
    sdk_version: str = SDK_VERSION


class ExtensionValidator:
    """Validate compatibility and importability before loading an extension."""

    def __init__(self) -> None:
        self._manifest_cache: dict[tuple[Path, int, int, str], ExtensionManifest] = {}
        self._compatibility_cache: dict[tuple[str, str, str], bool] = {}
        self._entry_point_cache: set[str] = set()

    def validate(
        self,
        manifest: ExtensionManifest,
        core_version: str = __version__,
    ) -> ExtensionManifest:
        compatibility_key = (manifest.minimum_core_version, manifest.sdk_version, core_version)
        compatible = self._compatibility_cache.get(compatibility_key)
        if compatible is None:
            compatible = (
                _version_key(manifest.minimum_core_version) <= _version_key(core_version)
                and manifest.sdk_version.split(".")[0] == SDK_VERSION.split(".")[0]
            )
            self._compatibility_cache[compatibility_key] = compatible
        if not compatible:
            raise ValidationError("Extension version is not compatible.")
        if ":" not in manifest.entry_point:
            raise ValidationError("entry_point must be module:attribute")

        module, attribute = manifest.entry_point.split(":", 1)
        if manifest.entry_point not in self._entry_point_cache:
            try:
                getattr(import_module(module), attribute)
            except (ImportError, AttributeError) as exc:
                raise ValidationError(f"Invalid extension entry point: {exc}") from exc
            self._entry_point_cache.add(manifest.entry_point)
        return manifest

    def load(self, path: Path) -> ExtensionManifest:
        """Read, validate, and return one extension manifest."""
        resolved = path.resolve()
        try:
            stat = path.stat()
            key = (resolved, stat.st_mtime_ns, stat.st_size, __version__)
            cached = self._manifest_cache.get(key)
            if cached is not None:
                return cached
            content = yaml.safe_load(path.read_text(encoding="utf-8"))
            manifest = self.validate(ExtensionManifest.model_validate(content))
            self._manifest_cache[key] = manifest
            return manifest
        except (OSError, yaml.YAMLError, ValueError) as exc:
            raise ValidationError(f"Invalid extension manifest: {exc}") from exc

    def clear_cache(self) -> None:
        self._manifest_cache.clear()
        self._compatibility_cache.clear()
        self._entry_point_cache.clear()

    def diagnostics(self) -> dict[str, object]:
        return {
            "manifest_cache_entries": len(self._manifest_cache),
            "compatibility_cache_entries": len(self._compatibility_cache),
            "entry_point_cache_entries": len(self._entry_point_cache),
        }


def _version_key(value: str) -> tuple[int, int, int, int, int]:
    """Compare semantic release candidates without adding a runtime dependency."""

    match = _VERSION_PATTERN.fullmatch(value.strip())
    if match is None:
        raise ValidationError(f"Invalid version: {value}")
    major, minor, patch, prerelease, serial = match.groups()
    prerelease_rank = {"a": 0, "b": 1, "rc": 2, None: 3}[prerelease]
    return (
        int(major),
        int(minor or 0),
        int(patch or 0),
        prerelease_rank,
        int(serial or 0),
    )
