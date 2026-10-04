from __future__ import annotations

from dataclasses import dataclass

import pytest

from manga_director.adapters.image_generator import ImageResult
from manga_director.agents import (
    ApprovalAgent,
    BaseAgent,
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
from manga_director.workflow import WorkflowContext


@dataclass
class MockImageGenerator:
    calls: list[str]

    def generate(self, prompt: str) -> ImageResult:
        self.calls.append(prompt)
        return ImageResult(
            success=True,
            image_path="memory://page-001.png",
            metadata={},
            provider="test",
            elapsed_time=0.0,
            messages=["test image"],
        )


def test_all_agents_are_stateless_base_agents() -> None:
    generator = MockImageGenerator([])
    agents = [
        PageDesignAgent(),
        EditorAgent(),
        StoryboardAgent(),
        DialogueAgent(),
        PromptAgent(),
        ImageAgent(generator),
        QualityAgent(),
        ContinuityAgent(),
        ApprovalAgent(),
    ]

    assert all(isinstance(agent, BaseAgent) for agent in agents)
    assert all(callable(agent.execute) for agent in agents)
    assert all(not hasattr(agent, "state") for agent in agents)


def test_page_design_agent_returns_all_required_design_fields() -> None:
    result = PageDesignAgent().execute(
        WorkflowContext(metadata={"page_design": {"panel_count": 3}})
    )

    assert result.state == PageState.DESIGNED
    assert set(result.payload) == {
        "page_type",
        "purpose",
        "reader_emotion",
        "featured_character",
        "big_moment",
        "hook",
        "panel_count",
        "panel_roles",
    }
    assert result.payload["panel_count"] == 3


def test_editor_and_storyboard_agents_review_and_create_complete_panels() -> None:
    design_context = WorkflowContext(
        state=PageState.DESIGNED,
        artifacts={
            "Designed": {
                "purpose": "Reveal the clue",
                "panel_count": 2,
                "panel_roles": ["setup", "hook"],
                "featured_character": "Aki",
                "big_moment": "clue appears",
                "hook": "Who left it?",
            }
        },
    )
    review = EditorAgent().execute(design_context)
    storyboard = StoryboardAgent().execute(design_context)

    assert all(review.payload["checks"].values())
    assert len(storyboard.payload["panels"]) == 2
    assert set(storyboard.payload["panels"][0]) >= {
        "composition",
        "camera",
        "characters",
        "background",
        "expression",
        "action",
        "dialogue",
        "sound_effect",
        "balloon_position",
    }


def test_dialogue_agent_makes_lines_compact() -> None:
    result = DialogueAgent().execute(
        WorkflowContext(metadata={"dialogue": ["  This   is a readable line.  "]})
    )

    assert result.state == PageState.STORYBOARDED
    assert result.payload["dialogue"] == ["This is a readable line."]


def test_prompt_agent_renders_the_markdown_template() -> None:
    result = PromptAgent().execute(
        WorkflowContext(
            page={"page_id": "1"},
            metadata={"character": {"name": "Aki"}},
            artifacts={
                "Designed": {"page_type": "drama", "purpose": "raise tension"},
                "Storyboarded": {"panels": [{"number": 1, "action": "turn"}]},
            },
        )
    )

    prompt = result.payload["prompt_markdown"]
    assert "# Manga page image prompt" in prompt
    assert "drama" in prompt
    assert "raise tension" in prompt
    assert result.payload["tokens"] > 0


def test_image_agent_delegates_to_the_image_generator_adapter() -> None:
    generator = MockImageGenerator([])
    result = ImageAgent(generator).execute(
        WorkflowContext(
            page={"id": "001"},
            artifacts={"PromptBuilt": {"prompt_markdown": "# prompt"}},
        )
    )

    assert result.state == PageState.GENERATED
    assert result.payload["image_path"] == "memory://page-001.png"
    assert generator.calls == ["# prompt"]


@pytest.mark.parametrize(
    ("scores", "passed"),
    [({"readability": 4}, True), ({"readability": 3}, False)],
)
def test_quality_agent_uses_four_of_five_as_the_pass_threshold(
    scores: dict[str, int], passed: bool
) -> None:
    result = QualityAgent().execute(WorkflowContext(metadata={"quality_scores": scores}))

    assert result.state == PageState.QUALITY_CHECKED
    assert result.payload["passed"] is passed


def test_continuity_agent_reports_differences_and_approval_requires_a_human() -> None:
    continuity = ContinuityAgent().execute(
        WorkflowContext(
            metadata={
                "previous_page": {"character": "Aki", "costume": "coat"},
                "current_page": {"character": "Aki", "costume": "uniform"},
            }
        )
    )
    approval = ApprovalAgent().execute(WorkflowContext(metadata={"approved_by": "editor"}))

    assert continuity.payload["consistent"] is False
    assert continuity.payload["warnings"] == ["Continuity mismatch: costume."]
    assert approval.state == PageState.APPROVED
    assert approval.payload["approved_by"] == "editor"


def test_approval_agent_rejects_missing_human_identity() -> None:
    with pytest.raises(ValueError, match="approved_by"):
        ApprovalAgent().execute(WorkflowContext())
