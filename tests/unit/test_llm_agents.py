from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import pytest

from manga_director.adapters.llm_provider import LLMResult, PromptRequest
from manga_director.agents import (
    DialogueAgent,
    EditorAgent,
    PageDesignAgent,
    QualityAgent,
    StoryboardAgent,
)
from manga_director.domain.state_machine import PageState
from manga_director.workflow import WorkflowContext


@dataclass
class RecordingLLM:
    requests: list[PromptRequest] = field(default_factory=list)

    def generate(self, request: PromptRequest) -> LLMResult:
        self.requests.append(request)
        return LLMResult(
            success=True,
            content="advisory",
            usage={},
            provider="recording",
            elapsed_time=0.0,
            finish_reason="stop",
            metadata={},
            messages=[],
        )


def _designed_context() -> WorkflowContext:
    return WorkflowContext(
        state=PageState.DESIGNED,
        artifacts={
            "Designed": {
                "purpose": "Reveal one clue",
                "panel_count": 1,
                "panel_roles": ["hook"],
                "featured_character": "Aki",
                "big_moment": "A clue appears",
                "hook": "Why now?",
            }
        },
    )


def _storyboard_context() -> WorkflowContext:
    return WorkflowContext(
        state=PageState.STORYBOARDED,
        artifacts={"Storyboarded": {"panels": [{"number": 1, "action": "turn"}]}},
    )


@pytest.mark.parametrize(
    ("agent_builder", "context_builder"),
    [
        (PageDesignAgent, WorkflowContext),
        (EditorAgent, _designed_context),
        (StoryboardAgent, _designed_context),
        (DialogueAgent, lambda: WorkflowContext(metadata={"dialogue": ["hello"]})),
        (QualityAgent, lambda: WorkflowContext(metadata={"quality_scores": {"readability": 5}})),
    ],
)
def test_llm_enabled_agents_use_the_provider_neutral_request_boundary(
    agent_builder: Callable[[RecordingLLM], Any],
    context_builder: Callable[[], WorkflowContext],
) -> None:
    provider = RecordingLLM()
    agent = agent_builder(provider)

    result = agent.execute(context_builder())

    assert result.success is True
    assert len(provider.requests) == 1
    request = provider.requests[0]
    assert "# Manga workflow assistance" in request.user_prompt
    assert request.metadata["agent"].endswith("Agent")
    assert "LLM assistance completed by recording." in result.messages
