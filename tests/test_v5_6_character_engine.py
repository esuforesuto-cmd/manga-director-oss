"""Contracts for the read-only v5.6 Character Engine v1."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.production import CharacterRegistryDTO, V56CharacterEngineService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _metadata() -> dict[str, object]:
    return {
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
        "story_context": {"chapter_goal": "Reveal the key witness."},
        "world_context": {"location": "station"},
        "timeline_context": {"events": [{"sequence": 1}]},
    }


def _context(*, metadata: dict[str, object] | None = None) -> WorkflowContext:
    return WorkflowContext(
        page={"id": "chapter-1-page-1"},
        metadata=metadata if metadata is not None else _metadata(),
    )


def test_character_profile_validation_uses_existing_evidence_without_mutation() -> None:
    context = _context()
    before = context.model_dump()
    report = V56CharacterEngineService().character_engine("chapter-1", context)

    assert report.analysis_only is True
    assert report.registry.page_count == 1
    assert report.profile.profile_valid is True
    assert report.summary.character_changed is False
    assert context.model_dump() == before


def test_relationship_consistency_requires_registered_relationship_targets() -> None:
    metadata = _metadata()
    character = metadata["character_context"]
    assert isinstance(character, dict)
    character["relationships"] = [{"target": "unknown", "type": "rival"}]

    report = V56CharacterEngineService().character_engine("chapter-1", _context(metadata=metadata))

    assert report.relationships.relationships_valid is False
    assert report.relationships.status == "needs_evidence"
    assert (
        "Each character relationship target must exist in the supplied registry."
        in report.summary.findings
    )


def test_character_arc_validation_requires_goal_stage_and_timeline_evidence() -> None:
    metadata = _metadata()
    character = metadata["character_context"]
    assert isinstance(character, dict)
    arc = character["arc"]
    assert isinstance(arc, dict)
    arc.pop("stage")

    report = V56CharacterEngineService().character_engine("chapter-1", _context(metadata=metadata))

    assert report.arc.arc_valid is False
    assert "Missing character arc stage evidence." in report.summary.findings


def test_appearance_consistency_requires_approved_visual_identity_evidence() -> None:
    metadata = _metadata()
    character = metadata["character_context"]
    assert isinstance(character, dict)
    appearance = character["appearance"]
    assert isinstance(appearance, dict)
    appearance.pop("accessories")

    report = V56CharacterEngineService().character_engine("chapter-1", _context(metadata=metadata))

    assert report.appearance.appearance_valid is False
    assert "Missing appearance profile evidence." in report.summary.findings


def test_dialogue_voice_consistency_requires_style_and_markers() -> None:
    metadata = _metadata()
    character = metadata["character_context"]
    assert isinstance(character, dict)
    voice = character["voice"]
    assert isinstance(voice, dict)
    voice["markers"] = []

    report = V56CharacterEngineService().character_engine("chapter-1", _context(metadata=metadata))

    assert report.dialogue_voice.voice_valid is False
    assert "Missing dialogue voice markers evidence." in report.summary.findings


def test_character_registry_rejects_more_than_one_page() -> None:
    with pytest.raises(ValidationError):
        CharacterRegistryDTO(
            project_id="chapter-1",
            page_reference="chapter-1-page-1",
            registry_evidence_available=False,
            page_count=2,
        )


def test_character_engine_keeps_delivery_repository_and_workflow_boundaries_out() -> None:
    source = (ROOT / "src/manga_director/production/v5_6_character_engine.py").read_text(
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


def test_character_engine_docs_are_available() -> None:
    assets = (
        "docs/CHARACTER_ENGINE.md",
        "docs/CHARACTER_REGISTRY.md",
        "docs/RELATIONSHIP_GRAPH.md",
        "docs/CHARACTER_ARC.md",
        "docs/APPEARANCE_CONSISTENCY.md",
        "docs/DIALOGUE_VOICE_PROFILE.md",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
