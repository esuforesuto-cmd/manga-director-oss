"""Contracts for the read-only v5.6 Page Engine v1."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.domain.state_machine import PageState
from manga_director.production import PagePlannerDTO, V56PageEngineService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _design() -> dict[str, object]:
    return {
        "purpose": "Reveal the witness.",
        "reader_emotion": "anticipation",
        "hook": "Who sent the ticket?",
        "big_moment": "The witness reveals the ticket.",
        "scene_transition": "Cut from platform to train car.",
        "panel_count": 3,
        "panel_roles": ["setup", "big moment", "hook"],
    }


def _storyboard() -> dict[str, object]:
    return {
        "panels": [
            {
                "number": 1,
                "camera": "wide shot",
                "composition": "platform establishes direction",
                "dialogue": ["The train is late."],
                "balloon_position": "upper right",
            },
            {
                "number": 2,
                "camera": "close-up",
                "composition": "ticket draws the eye",
                "dialogue": ["It was yours."],
                "balloon_position": "upper left",
            },
            {
                "number": 3,
                "camera": "medium shot",
                "composition": "door frames the departure",
                "dialogue": [],
                "balloon_position": "lower right",
            },
        ]
    }


def _context(
    *,
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
        metadata={
            "story_context": {"chapter_goal": "Reveal the witness."},
            "character_context": {"id": "aki"},
        },
    )


def test_page_structure_validation_uses_existing_evidence_without_mutation() -> None:
    context = _context()
    before = context.model_dump()
    report = V56PageEngineService().page_engine("chapter-1", context)

    assert report.analysis_only is True
    assert report.planner.page_count == 1
    assert report.panel_layout.layout_valid is True
    assert report.summary.layout_changed is False
    assert context.model_dump() == before


def test_panel_flow_validation_requires_contiguous_panel_order() -> None:
    storyboard = deepcopy(_storyboard())
    panels = storyboard["panels"]
    assert isinstance(panels, list)
    second_panel = panels[1]
    assert isinstance(second_panel, dict)
    second_panel["number"] = 3

    report = V56PageEngineService().page_engine("chapter-1", _context(storyboard=storyboard))

    assert report.panel_layout.layout_valid is False
    assert report.reader_flow.panel_order_valid is False


def test_reader_flow_validation_requires_declared_focal_direction() -> None:
    storyboard = deepcopy(_storyboard())
    panels = storyboard["panels"]
    assert isinstance(panels, list)
    first_panel = panels[0]
    assert isinstance(first_panel, dict)
    first_panel.pop("composition")

    report = V56PageEngineService().page_engine("chapter-1", _context(storyboard=storyboard))

    assert report.reader_flow.reader_flow_valid is False
    assert report.reader_flow.status == "needs_evidence"


def test_camera_consistency_requires_direction_for_each_panel() -> None:
    storyboard = deepcopy(_storyboard())
    panels = storyboard["panels"]
    assert isinstance(panels, list)
    last_panel = panels[-1]
    assert isinstance(last_panel, dict)
    last_panel.pop("camera")

    report = V56PageEngineService().page_engine("chapter-1", _context(storyboard=storyboard))

    assert report.camera.camera_consistent is False
    assert "Missing or invalid camera direction evidence." in report.summary.findings


def test_dialogue_placement_validation_requires_balloon_position_for_each_line() -> None:
    storyboard = deepcopy(_storyboard())
    panels = storyboard["panels"]
    assert isinstance(panels, list)
    second_panel = panels[1]
    assert isinstance(second_panel, dict)
    second_panel.pop("balloon_position")

    report = V56PageEngineService().page_engine("chapter-1", _context(storyboard=storyboard))

    assert report.dialogue_layout.placement_valid is False
    assert report.dialogue_layout.positioned_dialogue_count == 1


def test_scene_transition_validation_requires_story_aligned_transition_evidence() -> None:
    design = _design()
    design.pop("scene_transition")

    report = V56PageEngineService().page_engine("chapter-1", _context(design=design))

    assert report.scene_transition.transition_valid is False
    assert "Missing or invalid scene transition evidence." in report.summary.findings


def test_impact_panel_requires_big_moment_role_and_page_hook() -> None:
    design = _design()
    design["panel_roles"] = ["setup", "reveal", "hook"]

    report = V56PageEngineService().page_engine("chapter-1", _context(design=design))

    assert report.impact_panel.impact_valid is False
    assert "Missing or invalid impact panel evidence." in report.summary.findings


def test_page_planner_rejects_more_than_one_page() -> None:
    with pytest.raises(ValidationError):
        PagePlannerDTO(
            project_id="chapter-1",
            page_reference="chapter-1-page-1",
            current_state=PageState.DRAFT,
            purpose_available=True,
            reader_emotion_available=True,
            hook_available=True,
            panel_count=3,
            page_count=2,
            status="ready",
        )


def test_page_engine_keeps_delivery_repository_and_workflow_boundaries_out() -> None:
    source = (ROOT / "src/manga_director/production/v5_6_page_engine.py").read_text(
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


def test_page_engine_docs_are_available() -> None:
    assets = (
        "docs/PAGE_ENGINE.md",
        "docs/PAGE_PLANNER.md",
        "docs/PANEL_LAYOUT_ENGINE.md",
        "docs/CAMERA_DIRECTOR.md",
        "docs/READER_FLOW_ENGINE.md",
        "docs/DIALOGUE_LAYOUT.md",
        "docs/SCENE_TRANSITION_MANAGER.md",
        "docs/IMPACT_PANEL_MANAGER.md",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
