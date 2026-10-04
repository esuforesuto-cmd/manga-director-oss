"""Contracts for the read-only v5.6 Manga Production Pipeline v1."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.domain.state_machine import PageState
from manga_director.production import PagePipelineDTO, V56ProductionPipelineService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context(
    *,
    state: PageState = PageState.PROMPT_BUILT,
    artifacts: dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
) -> WorkflowContext:
    return WorkflowContext(
        page={"id": "chapter-1-page-1"},
        state=state,
        artifacts=artifacts
        if artifacts is not None
        else {PageState.STORYBOARDED.value: {"panels": []}},
        metadata=metadata
        if metadata is not None
        else {
            "story_context": {"beat": "reveal"},
            "character_context": {"hero": "Aki"},
            "world_context": {"location": "station"},
            "timeline_context": {"scene": 4},
        },
    )


def test_production_pipeline_standardizes_one_page_without_workflow_mutation() -> None:
    context = _context()
    before = context.model_dump()
    report = V56ProductionPipelineService().production_pipeline("chapter-1", context)

    assert report.planning_only is True
    assert report.page.page_count == 1
    assert report.page.next_command == "generate"
    assert report.art.generation_allowed is True
    assert report.art.generation_performed is False
    assert report.review.approval_performed is False
    assert report.export.export_performed is False
    assert report.summary.workflow_changed is False
    assert report.summary.automatic_action_taken is False
    assert report.prompt_brief.duplicate_context_elided is True
    assert report.prompt_brief.reused_context_keys == (
        "story_context",
        "character_context",
        "world_context",
        "timeline_context",
    )
    assert context.model_dump() == before


def test_story_consistency_requires_explicit_story_evidence() -> None:
    report = V56ProductionPipelineService().production_pipeline(
        "chapter-1", _context(metadata={"timeline_context": {"scene": 4}})
    )

    assert report.story.status == "blocked"
    assert "Missing story_context evidence." in report.summary.findings


def test_character_consistency_requires_character_and_world_evidence() -> None:
    report = V56ProductionPipelineService().production_pipeline(
        "chapter-1",
        _context(
            metadata={
                "story_context": {"beat": "reveal"},
                "timeline_context": {"scene": 4},
                "world_context": {"location": "station"},
            }
        ),
    )

    assert report.character.status == "blocked"
    assert "Missing character_context evidence." in report.summary.findings


def test_timeline_consistency_requires_explicit_timeline_evidence() -> None:
    report = V56ProductionPipelineService().production_pipeline(
        "chapter-1",
        _context(
            metadata={
                "story_context": {"beat": "reveal"},
                "character_context": {"hero": "Aki"},
                "world_context": {"location": "station"},
            }
        ),
    )

    assert report.story.status == "blocked"
    assert "Missing timeline_context evidence." in report.summary.findings


def test_production_pipeline_blocks_art_without_the_state_machine_storyboard_artifact() -> None:
    report = V56ProductionPipelineService().production_pipeline(
        "chapter-1", _context(artifacts={"storyboard": {"panels": []}})
    )

    assert report.page.storyboard_persisted is False
    assert report.art.generation_allowed is False
    assert "Persist a storyboard before image generation." in report.summary.findings


def test_review_and_export_are_only_advisory_after_required_evidence() -> None:
    quality_report = V56ProductionPipelineService().production_pipeline(
        "chapter-1",
        _context(
            state=PageState.QUALITY_CHECKED,
            artifacts={
                PageState.STORYBOARDED.value: {"panels": []},
                PageState.QUALITY_CHECKED.value: {"status": "passed"},
            },
        ),
    )
    approved_report = V56ProductionPipelineService().production_pipeline(
        "chapter-1",
        _context(
            state=PageState.APPROVED,
            artifacts={
                PageState.STORYBOARDED.value: {"panels": []},
                PageState.QUALITY_CHECKED.value: {"status": "passed"},
            },
        ),
    )

    assert quality_report.review.quality_review_completed is True
    assert quality_report.review.approval_eligible is True
    assert quality_report.review.approval_performed is False
    assert approved_report.export.approval_completed is True
    assert approved_report.export.export_eligible is True
    assert approved_report.export.export_performed is False


def test_page_pipeline_rejects_more_than_one_page() -> None:
    with pytest.raises(ValidationError):
        PagePipelineDTO(
            project_id="chapter-1",
            page_reference="chapter-1-page-1",
            current_state=PageState.DRAFT,
            page_count=2,
            storyboard_persisted=False,
        )


def test_v5_6_pipeline_keeps_delivery_repository_and_workflow_engine_boundaries_out() -> None:
    source = (ROOT / "src/manga_director/production/v5_6_production_pipeline.py").read_text(
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


def test_v5_6_pipeline_docs_are_available() -> None:
    assets = (
        "docs/PRODUCTION_PIPELINE.md",
        "docs/STORY_PIPELINE.md",
        "docs/PAGE_PIPELINE.md",
        "docs/REVIEW_PIPELINE.md",
        "docs/EXPORT_PIPELINE.md",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
