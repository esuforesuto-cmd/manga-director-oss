"""Contracts for the read-only v5.6 Story Engine v1."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.domain.state_machine import PageState
from manga_director.production import ChapterPlannerDTO, V56StoryEngineService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _metadata() -> dict[str, object]:
    return {
        "chapter_id": "chapter-1",
        "story_context": {
            "premise": "Aki must expose the station's secret.",
            "chapter_goal": "Reveal the key witness.",
            "conflict": "Aki cannot trust the witness.",
            "ending_goal": "Aki chooses to protect the witness.",
        },
        "character_context": {"motivation": "Protect the missing sibling."},
        "world_context": {"location": "station", "rule": "The last train never stops."},
        "timeline_context": {
            "events": [{"sequence": 1}, {"sequence": 2}, {"sequence": 3}]
        },
        "foreshadow_context": {"setups": ["ticket"], "payoffs": ["ticket"]},
    }


def _context(*, metadata: dict[str, object] | None = None) -> WorkflowContext:
    return WorkflowContext(
        page={"id": "chapter-1-page-1"},
        state=PageState.REVIEWED,
        metadata=metadata if metadata is not None else _metadata(),
    )


def test_story_structure_validation_uses_declared_story_evidence_without_mutation() -> None:
    context = _context()
    before = context.model_dump()
    report = V56StoryEngineService().story_engine("chapter-1", context)

    assert report.analysis_only is True
    assert report.planner.status == "ready"
    assert report.validator.story_structure_valid is True
    assert report.chapter.page_count == 1
    assert report.summary.story_changed is False
    assert context.model_dump() == before


def test_character_motivation_validation_requires_explicit_motivation() -> None:
    metadata = _metadata()
    metadata["character_context"] = {"name": "Aki"}

    report = V56StoryEngineService().story_engine("chapter-1", _context(metadata=metadata))

    assert report.validator.character_motivation_valid is False
    assert report.conflict.status == "needs_evidence"
    assert "Missing character motivation evidence." in report.validator.findings


def test_timeline_validation_requires_unique_ascending_sequence_values() -> None:
    metadata = _metadata()
    metadata["timeline_context"] = {"events": [{"sequence": 2}, {"sequence": 1}]}

    report = V56StoryEngineService().story_engine("chapter-1", _context(metadata=metadata))

    assert report.validator.timeline_valid is False
    assert "Timeline events must use unique ascending sequence values." in report.validator.findings


def test_foreshadow_validation_requires_payoffs_to_reference_declared_setups() -> None:
    metadata = _metadata()
    metadata["foreshadow_context"] = {"setups": ["ticket"], "payoffs": ["key"]}

    report = V56StoryEngineService().story_engine("chapter-1", _context(metadata=metadata))

    assert report.foreshadow.payoff_references_valid is False
    assert report.foreshadow.status == "needs_evidence"
    assert "Each foreshadow payoff must reference a declared setup." in report.summary.findings


def test_ending_consistency_requires_ending_goal_and_resolved_foreshadowing() -> None:
    metadata = _metadata()
    story_context = metadata["story_context"]
    assert isinstance(story_context, dict)
    story_context.pop("ending_goal")

    report = V56StoryEngineService().story_engine("chapter-1", _context(metadata=metadata))

    assert report.ending.status == "needs_evidence"
    assert "Missing ending goal evidence." in report.summary.findings


def test_chapter_planner_rejects_more_than_one_page() -> None:
    with pytest.raises(ValidationError):
        ChapterPlannerDTO(
            page_reference="chapter-1-page-1",
            current_state=PageState.DRAFT,
            chapter_goal_available=True,
            page_count=2,
        )


def test_story_engine_keeps_delivery_repository_and_workflow_boundaries_out() -> None:
    source = (ROOT / "src/manga_director/production/v5_6_story_engine.py").read_text(
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


def test_story_engine_docs_are_available() -> None:
    assets = (
        "docs/STORY_ENGINE.md",
        "docs/STORY_PLANNER.md",
        "docs/STORY_VALIDATOR.md",
        "docs/CHAPTER_PLANNER.md",
        "docs/FORESHADOW_MANAGER.md",
        "docs/ENDING_PLANNER.md",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
