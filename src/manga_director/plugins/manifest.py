"""Manifest parsing for local plugins."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from manga_director.domain.exceptions import PluginManifestError

_PLUGIN_NAME = re.compile(r"^[a-zA-Z][a-zA-Z0-9_.-]*$")


class PluginManifest(BaseModel):
    """Declarative metadata stored in a plugin's ``plugin.yaml`` file."""

    model_config = ConfigDict(frozen=True)

    name: str
    version: str
    entry_point: str
    dependencies: list[str] = Field(default_factory=list)
    enabled: bool = True
    description: str = ""

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not _PLUGIN_NAME.fullmatch(value):
            raise ValueError(
                "must start with a letter and contain only letters, digits, '.', '_', or '-'"
            )
        return value

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value.strip()

    @field_validator("entry_point")
    @classmethod
    def validate_entry_point(cls, value: str) -> str:
        module, separator, attribute = value.partition(":")
        if not module or separator != ":" or not attribute:
            raise ValueError("must use the format 'module:attribute'")
        return value

    @field_validator("dependencies")
    @classmethod
    def validate_dependencies(cls, values: list[str]) -> list[str]:
        if len(values) != len(set(values)):
            raise ValueError("must not contain duplicate plugin names")
        invalid = [value for value in values if not _PLUGIN_NAME.fullmatch(value)]
        if invalid:
            raise ValueError(f"contains invalid plugin names: {', '.join(invalid)}")
        return values

    @classmethod
    def from_mapping(cls, raw: object, source: str) -> PluginManifest:
        try:
            if not isinstance(raw, dict):
                raise ValueError("manifest root must be a mapping")
            return cls.model_validate(raw)
        except ValueError as exc:
            raise PluginManifestError(f"Invalid plugin manifest '{source}': {exc}") from exc
