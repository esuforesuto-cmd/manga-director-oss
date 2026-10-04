"""Markdown rendering for validated, provider-neutral structured prompts."""

from __future__ import annotations

import re

from manga_director.prompting.contracts import PromptResult, PromptTemplate, StructuredPrompt


class PromptRenderer:
    """Render a structured prompt into a Markdown template."""

    def render(self, prompt: StructuredPrompt, template: PromptTemplate) -> PromptResult:
        rendered = template.content.format(**prompt.sections)
        return PromptResult(
            success=True,
            prompt=rendered,
            tokens=len(re.findall(r"\S+", rendered)),
            metadata={
                "page_number": prompt.page_number,
                "template": template.name,
                "template_source": template.source,
                "template_hash": template.content_hash,
                "structured_prompt": prompt.model_dump(mode="json"),
            },
            messages=["Prompt rendered from Markdown template."],
        )
