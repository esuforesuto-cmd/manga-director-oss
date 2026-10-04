from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import yaml

from manga_director.domain.exceptions import ConfigurationError
from manga_director.domain.project import Project

SerializationFormat = Literal["json", "yaml"]


class ProjectSerializer:
    """Converts Project aggregates to/from JSON or YAML without filesystem ownership."""

    def __init__(self, format: SerializationFormat = "json") -> None:
        self.format = format

    def dumps(self, project: Project) -> str:
        data = project.model_dump(mode="json")
        if self.format == "json":
            return json.dumps(data, ensure_ascii=False, indent=2)
        return str(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))

    def loads(self, payload: str) -> Project:
        try:
            data = json.loads(payload) if self.format == "json" else yaml.safe_load(payload)
            return Project.model_validate(data)
        except (json.JSONDecodeError, yaml.YAMLError, ValueError) as exc:
            raise ConfigurationError(f"Unable to deserialize project: {exc}") from exc

    @staticmethod
    def for_path(path: Path) -> ProjectSerializer:
        suffix = path.suffix.lower()
        if suffix == ".json":
            return ProjectSerializer("json")
        if suffix in {".yaml", ".yml"}:
            return ProjectSerializer("yaml")
        raise ConfigurationError("Project files must use .json, .yaml, or .yml.")
