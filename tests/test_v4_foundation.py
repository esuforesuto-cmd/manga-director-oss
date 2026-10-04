"""Contracts for the v4 Creative Operating System foundations."""

from __future__ import annotations

from pathlib import Path

from manga_director.domain.project import Chapter, Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production import V4FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _service() -> tuple[V4FoundationService, InMemoryRepository]:
    repository = InMemoryRepository()
    repository.save(
        Project(
            id="pilot",
            title="Pilot",
            chapters=[Chapter(id="one", title="One", page_numbers=[1])],
            pages=[Page(page_number=1, storyboard={"panels": []})],
            metadata={"reference": "redacted", "world": "redacted"},
        )
    )
    return V4FoundationService(repository), repository


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}, "prompt": {"text": "redacted"}},
        metadata={"workflow_history": [{"step": "prompt", "to": "PromptBuilt"}]},
    )


def test_workspace_foundation_is_read_only_and_cannot_change_workflow() -> None:
    service, repository = _service()

    report = service.workspace("pilot", _context())

    assert report.analysis_only is True
    assert report.workspace.repository_read_only is True
    assert report.session.session_started is False
    assert report.snapshot.snapshot_persisted is False
    assert report.timeline.timeline_persisted is False
    assert report.timeline.workflow_changed is False
    assert report.summary.automatic_action_taken is False
    assert repository.load("pilot").metadata["world"] == "redacted"


def test_creative_memory_is_bounded_and_cannot_persist_or_retrieve_remotely() -> None:
    service, _ = _service()

    report = service.memory("pilot", _context())

    assert report.analysis_only is True
    assert report.story.memory_persisted is False
    assert report.character.memory_persisted is False
    assert report.world.memory_persisted is False
    assert report.style.memory_persisted is False
    assert report.production.memory_persisted is False
    assert report.index.index_persisted is False
    assert report.index.remote_lookup_performed is False


def test_creative_graph_is_repository_derived_and_never_persists_or_repairs() -> None:
    service, _ = _service()

    report = service.graph("pilot", _context())

    assert report.analysis_only is True
    assert report.story.repository_read_only is True
    assert report.character.repository_read_only is True
    assert all(node.persisted is False for node in report.story.nodes + report.character.nodes)
    assert all(edge.persisted is False for edge in report.story.edges + report.character.edges)
    assert report.summary.graph_persisted is False
    assert report.summary.automatic_action_taken is False


def test_creative_quality_is_diagnostic_and_cannot_complete_review_or_approve() -> None:
    service, _ = _service()

    report = service.quality("pilot", _context())

    assert report.analysis_only is True
    assert report.story.quality_score_computed is False
    assert report.story.story_changed is False
    assert report.character.consistency_enforced is False
    assert report.character.character_changed is False
    assert report.visual.visual_changed is False
    assert report.visual.image_generated is False
    assert report.editorial.review_completed is False
    assert report.editorial.approval_granted is False
    assert report.summary.quality_enforced is False


def test_v4_foundation_docs_examples_and_benchmarks_are_available() -> None:
    assets = (
        "docs/CREATIVE_WORKSPACE_FOUNDATION.md",
        "docs/CREATIVE_MEMORY_FOUNDATION.md",
        "docs/CREATIVE_GRAPH_FOUNDATION.md",
        "docs/CREATIVE_QUALITY_FOUNDATION.md",
        "docs/V4_ITERATION_1_FOUNDATION_REPORT.md",
        "examples/workspace_foundation/run.py",
        "examples/creative_memory/v4_foundation.py",
        "examples/creative_graph/v4_foundation.py",
        "examples/creative_quality/v4_foundation.py",
        "benchmarks/workspace_v4.py",
        "benchmarks/memory_v4.py",
        "benchmarks/graph_v4.py",
        "benchmarks/quality_v4.py",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
