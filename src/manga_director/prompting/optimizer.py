"""Deterministic, provider-neutral prompt text optimization."""

from __future__ import annotations

import re

from manga_director.prompting.contracts import StructuredPrompt


class PromptOptimizer:
    """Remove redundant text without making LLM calls or selecting providers."""

    _provider_directive = re.compile(r"^\s*(provider|model)\s*:\s*.*$", re.IGNORECASE)

    def optimize(self, prompt: StructuredPrompt) -> StructuredPrompt:
        sections = {name: self._normalize(value) for name, value in prompt.sections.items()}
        return prompt.model_copy(
            update={
                "dialogue": self._deduplicate(prompt.dialogue),
                "sections": sections,
                "metadata": {**prompt.metadata, "optimizer": self.__class__.__name__},
            },
            deep=True,
        )

    def _normalize(self, value: str) -> str:
        lines = [" ".join(line.split()) for line in value.splitlines()]
        without_directives = [
            line for line in lines if line and not self._provider_directive.match(line)
        ]
        return "\n".join(self._deduplicate(without_directives))

    @staticmethod
    def _deduplicate(values: list[str]) -> list[str]:
        seen: set[str] = set()
        unique: list[str] = []
        for value in values:
            if value not in seen:
                seen.add(value)
                unique.append(value)
        return unique
