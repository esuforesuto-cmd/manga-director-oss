"""Validation rules for one-page structured prompts and Markdown templates."""

from __future__ import annotations

import re

from manga_director.domain.exceptions import ValidationError
from manga_director.prompting.contracts import PromptTemplate, PromptValidation, StructuredPrompt


class PromptValidator:
    """Reject incomplete, forbidden, oversized, or template-incompatible prompts."""

    _placeholders = re.compile(r"\{([a-z_]+)\}")
    _template_variables = {
        "page_number",
        "page_type",
        "purpose",
        "panels",
        "dialogue",
        "character",
        "world",
    }
    _required_template_variables = {"page_type", "purpose", "panels"}

    def __init__(
        self,
        *,
        forbidden_words: tuple[str, ...] = (),
        max_characters: int = 8000,
    ) -> None:
        self._forbidden_words = tuple(word.lower() for word in forbidden_words)
        self._max_characters = max_characters

    def validate(self, prompt: StructuredPrompt, template: PromptTemplate) -> PromptValidation:
        errors: list[str] = []
        if not prompt.page_number.strip():
            errors.append("page number is required")
        if not prompt.sections.get("purpose", "").strip():
            errors.append("page purpose is required")
        if not prompt.panels:
            errors.append("storyboard panels are required")
        if not str(prompt.character.get("name", "")).strip():
            errors.append("character information is required")
        variables = set(self._placeholders.findall(template.content))
        unknown = variables - self._template_variables
        missing = self._required_template_variables - variables
        if unknown:
            errors.append(f"template has unsupported variables: {', '.join(sorted(unknown))}")
        if missing:
            errors.append(f"template is missing required variables: {', '.join(sorted(missing))}")
        serialized = "\n".join(prompt.sections.values())
        if len(serialized) > self._max_characters:
            errors.append(f"structured prompt exceeds {self._max_characters} characters")
        lowered = serialized.lower()
        forbidden = [word for word in self._forbidden_words if word in lowered]
        if forbidden:
            errors.append(f"forbidden words found: {', '.join(forbidden)}")
        if errors:
            raise ValidationError(f"Prompt validation failed: {'; '.join(errors)}")
        warnings = []
        if not prompt.dialogue:
            warnings.append("No dialogue supplied for the page.")
        if not prompt.world:
            warnings.append("No world information supplied for the page.")
        return PromptValidation(warnings=warnings)
