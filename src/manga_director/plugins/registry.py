"""Registry for plugin-contributed extension points."""

from __future__ import annotations

from builtins import list as builtin_list
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from manga_director.domain.exceptions import PluginRegistrationError
from manga_director.plugins.contracts import PluginType


@dataclass(frozen=True)
class PluginContribution:
    """A named capability supplied by one active plugin."""

    name: str
    plugin_name: str
    plugin_type: PluginType
    value: Any
    metadata: Mapping[str, Any] = field(default_factory=dict)


class PluginRegistry:
    """Explicit, typed registry with no discovery or lifecycle responsibilities."""

    def __init__(self) -> None:
        self._contributions: dict[PluginType, dict[str, PluginContribution]] = {
            plugin_type: {} for plugin_type in PluginType
        }

    def register(
        self,
        plugin_type: PluginType | str,
        name: str,
        value: Any,
        *,
        plugin_name: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> PluginContribution:
        """Register one named contribution; duplicate type/name pairs are rejected."""
        normalized_type = self._normalize_type(plugin_type)
        normalized_name = self._normalize_name(name)
        if normalized_name in self._contributions[normalized_type]:
            raise PluginRegistrationError(
                f"Plugin contribution '{normalized_type.value}:{normalized_name}' is already registered."
            )
        contribution = PluginContribution(
            name=normalized_name,
            plugin_name=self._normalize_name(plugin_name),
            plugin_type=normalized_type,
            value=value,
            metadata=dict(metadata or {}),
        )
        self._contributions[normalized_type][normalized_name] = contribution
        return contribution

    def unregister(self, plugin_type: PluginType | str, name: str) -> PluginContribution:
        """Remove and return one contribution."""
        normalized_type = self._normalize_type(plugin_type)
        normalized_name = self._normalize_name(name)
        try:
            return self._contributions[normalized_type].pop(normalized_name)
        except KeyError as exc:
            raise PluginRegistrationError(
                f"Plugin contribution '{normalized_type.value}:{normalized_name}' is not registered."
            ) from exc

    def find(self, plugin_type: PluginType | str, name: str) -> PluginContribution | None:
        """Return a contribution when present, otherwise ``None``."""
        normalized_type = self._normalize_type(plugin_type)
        return self._contributions[normalized_type].get(self._normalize_name(name))

    def list(self, plugin_type: PluginType | str | None = None) -> builtin_list[PluginContribution]:
        """List contributions ordered by type and contribution name."""
        if plugin_type is not None:
            return sorted(
                self._contributions[self._normalize_type(plugin_type)].values(),
                key=lambda contribution: contribution.name,
            )
        return sorted(
            (
                contribution
                for values in self._contributions.values()
                for contribution in values.values()
            ),
            key=lambda contribution: (contribution.plugin_type.value, contribution.name),
        )

    def unregister_plugin(self, plugin_name: str) -> builtin_list[PluginContribution]:
        """Remove all contributions owned by one plugin during lifecycle shutdown."""
        normalized_name = self._normalize_name(plugin_name)
        removed: builtin_list[PluginContribution] = []
        for contributions in self._contributions.values():
            names = [
                name for name, item in contributions.items() if item.plugin_name == normalized_name
            ]
            removed.extend(contributions.pop(name) for name in names)
        return removed

    @staticmethod
    def _normalize_type(plugin_type: PluginType | str) -> PluginType:
        try:
            return PluginType(plugin_type)
        except ValueError as exc:
            raise PluginRegistrationError(f"Unsupported plugin type: {plugin_type}") from exc

    @staticmethod
    def _normalize_name(name: str) -> str:
        normalized = name.strip()
        if not normalized:
            raise PluginRegistrationError("Plugin contribution name is required.")
        return normalized
