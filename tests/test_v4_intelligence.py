"""Contracts for read-only v4 Creative Operating System intelligence."""

from __future__ import annotations

from pathlib import Path

from manga_director.domain.project import Chapter, Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production import V4IntelligenceService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _service() -> tuple[V4IntelligenceService, InMemoryRepository]:
    repository = InMemoryRepository()
    repository.save(
        Project(
            id="intelligence-pilot",
            title="Intelligence Pilot",
            chapters=[Chapter(id="one", title="One", page_numbers=[1])],
            pages=[Page(page_number=1, storyboard={"panels": []})],
            metadata={"reference": "redacted", "world": "redacted"},
        )
    )
    return V4IntelligenceService(repository), repository


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "intelligence-pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}, "prompt": {"text": "redacted"}},
        metadata={"workflow_history": [{"step": "prompt", "to": "PromptBuilt"}]},
    )


def test_workspace_intelligence_is_read_only_and_recommendations_are_non_executable() -> None:
    service, repository = _service()

    report = service.workspace("intelligence-pilot", _context())

    assert report.analysis_only is True
    assert report.analytics.activity.activity_persisted is False
    assert report.timeline.timeline_persisted is False
    assert report.timeline.workflow_changed is False
    assert report.health.health_enforced is False
    assert report.recommendations.automatic_action_taken is False
    assert repository.load("intelligence-pilot").metadata["world"] == "redacted"


def test_memory_intelligence_has_no_remote_lookup_persistence_or_mutation() -> None:
    service, _ = _service()

    report = service.memory("intelligence-pilot", _context())

    assert report.analysis_only is True
    assert report.insight.insight_persisted is False
    assert report.relationships.remote_lookup_performed is False
    assert report.coverage.coverage_enforced is False
    assert report.consistency.evidence_changed is False
    assert report.recommendations.automatic_action_taken is False


def test_graph_intelligence_reports_consistency_without_repair_or_persistence() -> None:
    service, _ = _service()

    report = service.graph("intelligence-pilot", _context())

    assert report.analysis_only is True
    assert report.analytics.analysis_persisted is False
    assert report.relationships.graph_changed is False
    assert report.consistency.consistent is True
    assert report.consistency.repair_performed is False
    assert report.dependencies.dependency_cycles_detected == 0
    assert report.insights.automatic_action_taken is False


def test_quality_intelligence_cannot_generate_complete_review_or_approve() -> None:
    service, _ = _service()

    dashboard = service.quality("intelligence-pilot", _context())

    assert dashboard.analysis_only is True
    assert dashboard.story.story_changed is False
    assert dashboard.character.consistency_enforced is False
    assert dashboard.character.character_changed is False
    assert dashboard.visual.image_generated is False
    assert dashboard.visual.visual_changed is False
    assert dashboard.editorial.review_completed is False
    assert dashboard.editorial.approval_granted is False
    assert dashboard.quality_enforced is False


def test_v4_intelligence_docs_examples_and_benchmarks_are_available() -> None:
    assets = (
        "docs/CREATIVE_WORKSPACE_INTELLIGENCE.md",
        "docs/CREATIVE_MEMORY_INTELLIGENCE.md",
        "docs/CREATIVE_GRAPH_INTELLIGENCE.md",
        "docs/CREATIVE_QUALITY_INTELLIGENCE.md",
        "docs/V4_ITERATION_2_INTELLIGENCE_REPORT.md",
        "examples/workspace_dashboard/v4_intelligence.py",
        "examples/memory_insights/v4_intelligence.py",
        "examples/graph_analysis/v4_intelligence.py",
        "examples/quality_dashboard/v4_intelligence.py",
        "benchmarks/workspace_analytics_v4.py",
        "benchmarks/memory_analysis_v4.py",
        "benchmarks/graph_analysis_v4.py",
        "benchmarks/quality_analysis_v4.py",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
