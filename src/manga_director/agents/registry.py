from __future__ import annotations

from pathlib import Path

from manga_director.adapters.image_generator import ImageGenerator
from manga_director.adapters.llm_provider import LLMProvider
from manga_director.agents.base import BaseAgent
from manga_director.agents.builtin import (
    ApprovalAgent,
    ContinuityAgent,
    DialogueAgent,
    EditorAgent,
    ImageAgent,
    PageDesignAgent,
    PromptAgent,
    QualityAgent,
    StoryboardAgent,
)
from manga_director.domain.state_machine import PageState
from manga_director.prompting import PromptPipeline


def primary_agents(
    generator: ImageGenerator,
    prompt_directory: Path | None = None,
    llm_provider: LLMProvider | None = None,
    prompt_pipeline: PromptPipeline | None = None,
) -> dict[PageState, BaseAgent]:
    return {
        PageState.DESIGNED: PageDesignAgent(llm_provider, prompt_directory),
        PageState.REVIEWED: EditorAgent(llm_provider, prompt_directory),
        PageState.STORYBOARDED: StoryboardAgent(llm_provider, prompt_directory),
        PageState.PROMPT_BUILT: PromptAgent(prompt_pipeline),
        PageState.GENERATED: ImageAgent(generator),
        PageState.QUALITY_CHECKED: QualityAgent(llm_provider, prompt_directory),
        PageState.APPROVED: ApprovalAgent(),
    }


def support_agents(
    llm_provider: LLMProvider | None = None,
    prompt_directory: Path | None = None,
) -> dict[str, BaseAgent]:
    return {
        "dialogue": DialogueAgent(llm_provider, prompt_directory),
        "continuity": ContinuityAgent(),
    }
