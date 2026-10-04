"""Markdown-only prompt template loading and future plugin registration."""

from __future__ import annotations

import hashlib
from importlib.resources import files
from pathlib import Path

from manga_director.domain.exceptions import ValidationError
from manga_director.prompting.contracts import PromptTemplate


class PromptTemplateLoader:
    """Loads package/project templates and accepts explicit future-plugin templates."""

    def __init__(self, prompt_directory: Path | None = None) -> None:
        self._prompt_directory = prompt_directory
        self._registered: dict[str, PromptTemplate] = {}

    def register(self, template: PromptTemplate) -> None:
        """Register a validated Markdown template from a future plugin composition root."""
        self._validate_name(template.name)
        self._registered[template.name] = template

    def load(self, name: str) -> PromptTemplate:
        """Load exactly one Markdown template without provider-based selection."""
        self._validate_name(name)
        try:
            return self._registered[name]
        except KeyError:
            pass
        content, source = self._read(name)
        return PromptTemplate(
            name=name,
            content=content,
            source=source,
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        )

    def _read(self, name: str) -> tuple[str, str]:
        if self._prompt_directory is not None:
            candidate = self._prompt_directory / name
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8"), str(candidate)
        template = files("manga_director.prompts").joinpath(name)
        try:
            return template.read_text(encoding="utf-8"), f"package:{name}"
        except FileNotFoundError as exc:
            raise ValidationError(f"Prompt template '{name}' was not found.") from exc

    @staticmethod
    def _validate_name(name: str) -> None:
        path = Path(name)
        if path.name != name or path.suffix != ".md":
            raise ValidationError("Prompt template names must be direct Markdown filenames.")
