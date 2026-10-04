"""End-to-end contracts for the read-only v5.6 Manga Production OS RC1."""

from __future__ import annotations

from manga_director.domain.state_machine import PageState
from manga_director.production import (
    V56CharacterEngineService,
    V56ExportEngineService,
    V56PageEngineService,
    V56ProductionPipelineService,
    V56ReviewEngineService,
    V56StoryEngineService,
)
from manga_director.workflow import WorkflowContext


def _context() -> WorkflowContext:
    page = {
        "id": "chapter-1-page-1",
        "character": "aki",
        "costume": "uniform",
        "props": "ticket",
        "time": "night",
        "location": "station",
        "emotion": "anticipation",
    }
    design = {
        "purpose": "Reveal the witness.",
        "reader_emotion": "anticipation",
        "hook": "Who sent the ticket?",
        "big_moment": "The witness reveals the ticket.",
        "scene_transition": "Cut from platform to train car.",
        "panel_count": 3,
        "panel_roles": ["setup", "big moment", "hook"],
    }
    storyboard = {
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
            {
                "number": 3,
                "camera": "medium shot",
                "composition": "door frames the departure",
                "background": "train car",
                "characters": ["aki"],
                "dialogue": [],
                "balloon_position": "lower right",
            },
        ]
    }
    return WorkflowContext(
        page=page,
        state=PageState.APPROVED,
        artifacts={
            PageState.DESIGNED.value: design,
            PageState.STORYBOARDED.value: storyboard,
            PageState.GENERATED.value: {"image_path": "chapter-1-page-1.png"},
            PageState.QUALITY_CHECKED.value: {"passed": True},
        },
        metadata={
            "chapter_id": "chapter-1",
            "story_context": {
                "premise": "Aki must expose the station's secret.",
                "chapter_goal": "Reveal the key witness.",
                "conflict": "Aki cannot trust the witness.",
                "ending_goal": "Aki chooses to protect the witness.",
            },
            "character_registry": {"aki": {"name": "Aki"}, "mio": {"name": "Mio"}},
            "character_context": {
                "id": "aki",
                "name": "Aki",
                "motivation": "Protect the missing sibling.",
                "relationships": [{"target": "mio", "type": "ally"}],
                "arc": {"goal": "Trust others", "stage": "doubt"},
                "appearance": {
                    "hair": "black bob",
                    "eyes": "brown",
                    "clothing": "school uniform",
                    "accessories": "silver ticket",
                },
                "voice": {"style": "direct", "markers": ["short replies"]},
            },
            "world_context": {"location": "station", "rule": "The last train never stops."},
            "timeline_context": {"events": [{"sequence": 1}, {"sequence": 2}]},
            "foreshadow_context": {"setups": ["ticket"], "payoffs": ["ticket"]},
            "previous_page": dict(page),
            "current_page": dict(page),
            "print_export": {"trim_size": "B5", "dpi": 600},
            "web_export": {"format": "webp", "width": 1440},
            "ebook_export": {"format": "epub", "reading_direction": "rtl"},
            "publishing_metadata": {
                "title": "Last Train",
                "language": "ja",
                "rights": "all-rights",
            },
        },
    )


def test_v5_6_rc1_validates_one_approved_page_across_all_engines_without_mutation() -> None:
    context = _context()
    before = context.model_dump()

    pipeline = V56ProductionPipelineService().production_pipeline("chapter-1", context)
    story = V56StoryEngineService().story_engine("chapter-1", context)
    character = V56CharacterEngineService().character_engine("chapter-1", context)
    page = V56PageEngineService().page_engine("chapter-1", context)
    review = V56ReviewEngineService().review_engine("chapter-1", context)
    export = V56ExportEngineService().export_engine("chapter-1", context)

    assert pipeline.page.page_count == 1
    assert pipeline.export.export_eligible is True
    assert story.validator.story_structure_valid is True
    assert story.validator.timeline_valid is True
    assert character.profile.profile_valid is True
    assert character.relationships.relationships_valid is True
    assert page.panel_layout.layout_valid is True
    assert page.reader_flow.reader_flow_valid is True
    assert review.quality.score == 100
    assert review.revision_advisor.suggestions == ()
    assert export.print_export.status == "ready"
    assert export.web_export.status == "ready"
    assert export.ebook_export.status == "ready"
    assert export.release_bundle.bundle_eligible is True
    assert export.archive.archive_integrity_valid is True
    assert pipeline.summary.workflow_changed is False
    assert story.summary.automatic_action_taken is False
    assert character.summary.automatic_action_taken is False
    assert page.summary.layout_changed is False
    assert review.quality.approval_granted is False
    assert export.summary.files_created == 0
    assert context.model_dump() == before
