"""Deterministic construction of provider-neutral structured prompts."""

from __future__ import annotations

import json

from manga_director.prompting.contracts import PromptInput, StructuredPrompt


class PromptBuilder:
    """Build a structured prompt from one page's approved source artifacts."""

    def build(self, source: PromptInput) -> StructuredPrompt:
        panels = source.storyboard.get("panels", [])
        normalized_panels = [panel for panel in panels if isinstance(panel, dict)]
        page_type = str(source.page_design.get("page_type", "manga"))
        purpose = str(source.page_design.get("purpose", ""))
        return StructuredPrompt(
            page_number=source.page_number,
            page_design=source.page_design,
            panels=normalized_panels,
            dialogue=source.dialogue,
            character=source.character,
            world=source.world,
            sections={
                "page_number": source.page_number,
                "page_type": page_type,
                "purpose": purpose,
                "panels": json.dumps(normalized_panels, ensure_ascii=False, sort_keys=True),
                "dialogue": json.dumps(source.dialogue, ensure_ascii=False),
                "character": json.dumps(source.character, ensure_ascii=False, sort_keys=True),
                "world": json.dumps(source.world, ensure_ascii=False, sort_keys=True),
            },
            metadata={"builder": self.__class__.__name__, **source.metadata},
        )
