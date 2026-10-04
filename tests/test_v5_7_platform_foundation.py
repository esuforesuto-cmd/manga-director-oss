"""Contracts for the v5.7 read-only Production Platform foundation."""

from __future__ import annotations

from pathlib import Path

import pytest

from manga_director.domain.state_machine import PageState
from manga_director.plugins import PluginRegistry, PluginType
from manga_director.production import V57ProductionPlatformFoundationService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "chapter-1-page-1"},
        state=PageState.QUALITY_CHECKED,
        artifacts={
            PageState.STORYBOARDED.value: {"panels": []},
            PageState.QUALITY_CHECKED.value: {"status": "passed"},
        },
        metadata={
            "story_context": {"beat": "reveal"},
            "character_context": {"hero": "Aki"},
            "world_context": {"location": "station"},
            "timeline_context": {"scene": 4},
            "automation_templates": ["quality-review"],
            "automation_rules": ["human-approval"],
        },
    )


def test_workspace_and_project_foundations_are_read_only_and_one_page_scoped() -> None:
    context = _context()
    before = context.model_dump()
    service = V57ProductionPlatformFoundationService()

    workspace = service.workspace("chapter-1", context)
    project = service.project("chapter-1", context)

    assert workspace.workspace.page_count == 1
    assert workspace.workspace.workspace_created is False
    assert workspace.workflow_mutated is False
    assert project.project.storyboard_persisted is True
    assert project.project.quality_review_completed is True
    assert project.required_state_authority == "StateMachine"
    assert context.model_dump() == before


def test_asset_lifecycle_foundation_observes_existing_evidence_without_repository_writes() -> None:
    report = V57ProductionPlatformFoundationService().assets("chapter-1", _context())

    assert report.summary.observed_asset_count == 8
    assert report.summary.artifact_asset_count == 2
    assert report.summary.metadata_asset_count == 6
    assert report.summary.lifecycle_changed is False
    assert report.summary.repository_mutated is False
    assert all(asset.lifecycle_state == "observed" for asset in report.assets)
    assert all(asset.asset_persisted is False for asset in report.assets)


def test_asset_manager_keeps_artifact_and_metadata_provenance_distinct() -> None:
    context = WorkflowContext(
        page={"id": "chapter-1-page-1"},
        state=PageState.STORYBOARDED,
        artifacts={"reference": {"source": "storyboard"}},
        metadata={"reference": {"source": "production"}},
    )
    before = context.model_dump()

    report = V57ProductionPlatformFoundationService().assets("chapter-1", context)

    assert [(asset.source_kind, asset.source_key) for asset in report.assets] == [
        ("artifact", "reference"),
        ("metadata", "reference"),
    ]
    assert len({asset.asset_id for asset in report.assets}) == 2
    assert report.summary.artifact_asset_count == 1
    assert report.summary.metadata_asset_count == 1
    assert context.model_dump() == before


def test_automation_foundation_reuses_references_without_execution_or_workflow_mutation() -> None:
    report = V57ProductionPlatformFoundationService().automation("chapter-1", _context())

    assert report.automation.template_references == ("quality-review",)
    assert report.automation.rule_references == ("human-approval",)
    assert report.automation.human_approval_required is True
    assert report.automation.execution_requested is False
    assert report.automation.execution_performed is False
    assert report.automation.workflow_mutated is False
    assert report.source_contract == "existing_automation_engine_unchanged"


def test_plugin_runtime_reads_existing_registry_without_plugin_lifecycle_actions() -> None:
    registry = PluginRegistry()
    registry.register(PluginType.PROMPT, "page-review", object(), plugin_name="review-tools")

    report = V57ProductionPlatformFoundationService(registry).plugin_runtime()

    assert report.summary.registry_observed is True
    assert report.summary.contribution_count == 1
    assert report.descriptors[0].contribution_name == "page-review"
    assert report.descriptors[0].plugin_loaded_by_service is False
    assert report.summary.plugin_runtime_mutated is False


def test_platform_foundation_rejects_multi_page_context() -> None:
    context = _context().model_copy(update={"page": {"pages": [{"id": "one"}, {"id": "two"}]}})

    with pytest.raises(ValueError, match="exactly one Page"):
        V57ProductionPlatformFoundationService().foundation("chapter-1", context)


def test_v5_7_foundation_keeps_delivery_repository_and_lifecycle_boundaries_out() -> None:
    source = (ROOT / "src/manga_director/production/v5_7_platform_foundation.py").read_text(
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


def test_v5_7_foundation_docs_are_available() -> None:
    documents = (
        "docs/WORKSPACE_MANAGER.md",
        "docs/PROJECT_MANAGER.md",
        "docs/ASSET_MANAGER.md",
        "docs/AUTOMATION_FOUNDATION.md",
        "docs/PLUGIN_RUNTIME.md",
    )

    assert all((ROOT / document).is_file() for document in documents)
