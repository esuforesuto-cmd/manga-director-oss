"""Contracts for the read-only v5.6 Review Engine v1."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.domain.state_machine import PageState
from manga_director.production import QualityScoringEngineDTO, V56ReviewEngineService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _design() -> dict[str, object]:
    return {"panel_roles": ["setup", "big moment"], "purpose": "Reveal the ticket."}


def _storyboard() -> dict[str, object]:
    return {
        "panels": [
            {
                "number": 1,
                "camera": "wide shot",
                "composition": "platform establishes direction",
                "background": "station platform",
                "characters": ["aki"],
                "dialogue": ["The train is late."],
                "balloon_position": "upper right",
            },
            {
                "number": 2,
                "camera": "close-up",
                "composition": "ticket draws the eye",
                "background": "train door",
                "characters": ["aki", "mio"],
                "dialogue": ["It was yours."],
                "balloon_position": "upper left",
            },
        ]
    }


def _metadata() -> dict[str, object]:
    page = {
        "character": "aki",
        "costume": "uniform",
        "props": "ticket",
        "time": "night",
        "location": "station",
        "emotion": "anticipation",
    }
    return {
        "story_context": {"premise": "Aki seeks the truth.", "chapter_goal": "Reveal ticket."},
        "character_context": {
            "name": "Aki",
            "motivation": "Protect a sibling.",
            "voice": {"style": "direct"},
        },
        "previous_page": dict(page),
        "current_page": dict(page),
    }


def _context(
    *,
    metadata: dict[str, object] | None = None,
    design: dict[str, object] | None = None,
    storyboard: dict[str, object] | None = None,
) -> WorkflowContext:
    return WorkflowContext(
        page={"id": "chapter-1-page-1"},
        state=PageState.STORYBOARDED,
        artifacts={
            PageState.DESIGNED.value: design if design is not None else _design(),
            PageState.STORYBOARDED.value: storyboard if storyboard is not None else _storyboard(),
        },
        metadata=metadata if metadata is not None else _metadata(),
    )


def test_story_review_validation_uses_existing_evidence_without_mutation() -> None:
    context = _context()
    before = context.model_dump()
    report = V56ReviewEngineService().review_engine("chapter-1", context)

    assert report.analysis_only is True
    assert report.story.status == "ready"
    assert report.quality.score == 100
    assert report.revision_advisor.suggestions == ()
    assert context.model_dump() == before


def test_character_review_validation_requires_name_and_motivation() -> None:
    metadata = _metadata()
    character = metadata["character_context"]
    assert isinstance(character, dict)
    character.pop("motivation")

    report = V56ReviewEngineService().review_engine("chapter-1", _context(metadata=metadata))

    assert report.character.status == "needs_review"
    assert any(suggestion.area == "character" for suggestion in report.revision_advisor.suggestions)


def test_page_review_validation_requires_matching_panel_role_evidence() -> None:
    design = _design()
    design["panel_roles"] = ["setup"]

    report = V56ReviewEngineService().review_engine("chapter-1", _context(design=design))

    assert report.page.panel_count_matches is False
    assert report.page.status == "needs_review"


def test_art_review_validation_requires_visual_direction_for_each_panel() -> None:
    storyboard = deepcopy(_storyboard())
    panels = storyboard["panels"]
    assert isinstance(panels, list)
    panel = panels[0]
    assert isinstance(panel, dict)
    panel.pop("background")

    report = V56ReviewEngineService().review_engine("chapter-1", _context(storyboard=storyboard))

    assert report.art.visual_direction_complete is False
    assert any(suggestion.area == "art" for suggestion in report.revision_advisor.suggestions)


def test_dialogue_review_validation_requires_placement_and_voice_evidence() -> None:
    storyboard = deepcopy(_storyboard())
    panels = storyboard["panels"]
    assert isinstance(panels, list)
    panel = panels[1]
    assert isinstance(panel, dict)
    panel.pop("balloon_position")

    report = V56ReviewEngineService().review_engine("chapter-1", _context(storyboard=storyboard))

    assert report.dialogue.status == "needs_review"
    assert report.dialogue.positioned_dialogue_count == 1


def test_continuity_validation_reports_only_declared_mismatches() -> None:
    metadata = _metadata()
    current = metadata["current_page"]
    assert isinstance(current, dict)
    current["costume"] = "coat"

    report = V56ReviewEngineService().review_engine("chapter-1", _context(metadata=metadata))

    assert report.continuity.mismatched_fields == ("costume",)
    assert report.continuity.status == "needs_review"


def test_quality_score_validation_is_bounded_and_never_approves() -> None:
    report = V56ReviewEngineService().review_engine("chapter-1", _context())

    assert report.quality.score == 100
    assert report.quality.approval_granted is False
    with pytest.raises(ValidationError):
        QualityScoringEngineDTO(score=101, passed_dimensions=6)


def test_review_engine_keeps_delivery_repository_and_workflow_boundaries_out() -> None:
    source = (ROOT / "src/manga_director/production/v5_6_review_engine.py").read_text(
        encoding="utf-8"
    )

    for forbidden in (
        "manga_director.api",
        "manga_director.cli",
        "manga_director.mcp",
        "manga_director.repositories",
        "workflow.engine",
        ".execute(",
        ".advance(",
        "save(",
    ):
        assert forbidden not in source


def test_review_engine_docs_are_available() -> None:
    assets = (
        "docs/REVIEW_ENGINE.md",
        "docs/STORY_REVIEWER.md",
        "docs/CHARACTER_REVIEWER.md",
        "docs/PAGE_REVIEWER.md",
        "docs/ART_REVIEWER.md",
        "docs/DIALOGUE_REVIEWER.md",
        "docs/CONTINUITY_REVIEWER.md",
        "docs/QUALITY_SCORING_ENGINE.md",
        "docs/REVISION_ADVISOR.md",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
