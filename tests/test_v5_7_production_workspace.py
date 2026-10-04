"""Contracts for the v5.7 read-only Production Workspace v2."""

from __future__ import annotations

from pathlib import Path

import pytest

from manga_director.domain.state_machine import PageState
from manga_director.production import (
    ProductionTemplateDTO,
    ResourceAllocationDTO,
    V57ProductionWorkspaceService,
)
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "chapter-2-page-1"},
        state=PageState.QUALITY_CHECKED,
        artifacts={
            PageState.STORYBOARDED.value: {"panels": []},
            PageState.QUALITY_CHECKED.value: {"status": "passed"},
        },
        metadata={
            "story_context": {"beat": "decision"},
            "workflow_history": [{"step": "quality"}],
        },
    )


def test_asset_registry_observes_lifecycle_evidence_without_registry_or_repository_writes() -> None:
    report = V57ProductionWorkspaceService().asset_registry("chapter-2", _context())

    assert report.lifecycle_valid is True
    assert report.registry_persisted is False
    assert report.repository_mutated is False
    assert report.unique_source_keys == (
        "QualityChecked",
        "Storyboarded",
        "story_context",
        "workflow_history",
    )


def test_asset_registry_keeps_distinct_provenance_for_a_shared_source_key() -> None:
    context = WorkflowContext(
        page={"id": "chapter-2-page-1"},
        state=PageState.STORYBOARDED,
        artifacts={"reference": {"source": "storyboard"}},
        metadata={"reference": {"source": "production"}},
    )
    before = context.model_dump()

    report = V57ProductionWorkspaceService().asset_registry("chapter-2", context)

    assert report.unique_source_keys == ("reference",)
    assert [(entry.source_kind, entry.source_key) for entry in report.entries] == [
        ("artifact", "reference"),
        ("metadata", "reference"),
    ]
    assert len({entry.asset_id for entry in report.entries}) == 2
    assert context.model_dump() == before


def test_asset_storage_reports_explicit_references_without_storage_access() -> None:
    context = _context()
    before = context.model_dump()
    storyboard_asset_id = "asset:chapter-2:chapter-2-page-1:artifact:Storyboarded"

    report = V57ProductionWorkspaceService().asset_storage(
        "chapter-2",
        context,
        {storyboard_asset_id: " project://chapter-2/storyboard.json "},
    )

    storyboard_record = next(
        record for record in report.records if record.asset.asset_id == storyboard_asset_id
    )
    assert storyboard_record.storage_reference == "project://chapter-2/storyboard.json"
    assert storyboard_record.storage_evidence_present is True
    assert storyboard_record.storage_accessed is False
    assert storyboard_record.storage_written is False
    assert report.storage_evidence_count == 1
    assert len(report.unresolved_asset_ids) == len(report.records) - 1
    assert report.repository_mutated is False
    assert context.model_dump() == before


def test_asset_cache_is_keyed_by_evidence_and_explicitly_refreshable() -> None:
    context = _context()
    before = context.model_dump()
    service = V57ProductionWorkspaceService()

    first = service.asset_cache("chapter-2", context)
    second = service.asset_cache("chapter-2", context)
    refreshed = service.asset_cache("chapter-2", context, refresh=True)

    assert first.cache_hit is False
    assert second.cache_hit is True
    assert second.cache_key == first.cache_key
    assert second.assets == first.assets
    assert refreshed.cache_hit is False
    assert refreshed.cache_key == first.cache_key
    assert refreshed.cache_persisted is False
    assert refreshed.repository_mutated is False
    assert context.model_dump() == before


def test_asset_versioning_reports_explicit_evidence_without_changing_history() -> None:
    context = _context()
    before = context.model_dump()
    storyboard_asset_id = "asset:chapter-2:chapter-2-page-1:artifact:Storyboarded"

    report = V57ProductionWorkspaceService().asset_versioning(
        "chapter-2",
        context,
        {storyboard_asset_id: "v3"},
    )

    storyboard_version = next(
        version for version in report.versions if version.asset.asset_id == storyboard_asset_id
    )
    assert storyboard_version.version_reference == "v3"
    assert storyboard_version.version_evidence_present is True
    assert storyboard_version.version_created is False
    assert storyboard_version.version_replaced is False
    assert storyboard_version.version_history_mutated is False
    assert report.version_evidence_count == 1
    assert len(report.unresolved_asset_ids) == len(report.versions) - 1
    assert report.repository_mutated is False
    assert context.model_dump() == before


def test_asset_import_export_reports_evidence_without_transferring_assets() -> None:
    context = _context()
    before = context.model_dump()
    storyboard_asset_id = "asset:chapter-2:chapter-2-page-1:artifact:Storyboarded"

    report = V57ProductionWorkspaceService().asset_import_export(
        "chapter-2",
        context,
        import_references={storyboard_asset_id: "source://storyboard"},
        export_references={storyboard_asset_id: "target://storyboard"},
    )

    imported = next(item for item in report.imports if item.asset.asset_id == storyboard_asset_id)
    exported = next(item for item in report.exports if item.asset.asset_id == storyboard_asset_id)
    assert imported.import_reference == "source://storyboard"
    assert imported.import_evidence_present is True
    assert imported.import_requested is False
    assert imported.import_performed is False
    assert exported.export_reference == "target://storyboard"
    assert exported.export_evidence_present is True
    assert exported.export_requested is False
    assert exported.export_performed is False
    assert report.import_evidence_count == 1
    assert report.export_evidence_count == 1
    assert len(report.unresolved_import_asset_ids) == len(report.imports) - 1
    assert len(report.unresolved_export_asset_ids) == len(report.exports) - 1
    assert report.repository_mutated is False
    assert context.model_dump() == before


def test_project_workspace_and_workflow_state_are_consistent_and_read_only() -> None:
    context = _context()
    before = context.model_dump()
    service = V57ProductionWorkspaceService()

    workspace = service.project_workspace("chapter-2", context)
    workflow = service.workflow_state("chapter-2", context)

    assert workspace.workspace.page_count == 1
    assert workspace.workspace.workspace_consistent is True
    assert workspace.workflow_state_owned_by == "StateMachine"
    assert workflow.valid is True
    assert workflow.state.next_command == "approve"
    assert workflow.state.state_changed is False
    assert context.model_dump() == before


def test_resource_manager_validates_capacity_and_scope_without_allocation() -> None:
    context = _context()
    allocation = ResourceAllocationDTO(
        resource_id="artist:chapter-2:page-1",
        project_id="chapter-2",
        page_reference="chapter-2-page-1",
        owner="human-artist",
        requested_units=2,
        available_units=1,
    )

    report = V57ProductionWorkspaceService().resources("chapter-2", context, (allocation,))

    assert report.allocation_valid is False
    assert report.insufficient_resource_ids == ("artist:chapter-2:page-1",)
    assert report.allocation_mutated is False
    assert report.allocations[0].allocation_performed is False


def test_template_registry_validates_evidence_and_single_page_compatibility() -> None:
    template = ProductionTemplateDTO(
        template_id="quality-review",
        page_reference="chapter-2-page-1",
        required_evidence=("Storyboarded", "QualityChecked"),
    )

    report = V57ProductionWorkspaceService().templates("chapter-2", _context(), (template,))

    assert report.compatible is True
    assert report.missing_evidence == ()
    assert report.registry_mutated is False


def test_session_recovery_is_diagnostic_only_and_requires_existing_checkpoint_evidence() -> None:
    report = V57ProductionWorkspaceService().production_session("chapter-2", _context())

    assert report.session.checkpoint_evidence_available is True
    assert report.session.recovery_eligible is True
    assert report.session.resumed is False
    assert report.recovery_performed is False
    assert report.workflow_mutated is False


def test_production_workspace_rejects_multiple_pages() -> None:
    context = _context().model_copy(update={"page": {"pages": [{"id": "one"}, {"id": "two"}]}})

    with pytest.raises(ValueError, match="exactly one Page"):
        V57ProductionWorkspaceService().production_workspace("chapter-2", context)


def test_v5_7_workspace_keeps_delivery_repository_and_workflow_engine_boundaries_out() -> None:
    source = (ROOT / "src/manga_director/production/v5_7_production_workspace.py").read_text(
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


def test_v5_7_production_workspace_docs_are_available() -> None:
    documents = (
        "docs/ASSET_REGISTRY.md",
        "docs/ASSET_STORAGE.md",
        "docs/ASSET_CACHE.md",
        "docs/ASSET_VERSIONING.md",
        "docs/ASSET_IMPORT_EXPORT.md",
        "docs/PROJECT_WORKSPACE.md",
        "docs/WORKFLOW_STATE_MANAGER.md",
        "docs/RESOURCE_MANAGER.md",
        "docs/TEMPLATE_REGISTRY.md",
        "docs/PRODUCTION_SESSION_MANAGER.md",
    )

    assert all((ROOT / document).is_file() for document in documents)
