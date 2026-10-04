"""Contracts for the non-executing v4.3 Creative Production Platform foundation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.domain.state_machine import PageState
from manga_director.production import ProductionProjectDTO, V43ProductionFoundationService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}},
        metadata={"provenance": "human"},
    )


def test_production_pipeline_foundation_is_one_page_and_cannot_change_workflow() -> None:
    report = V43ProductionFoundationService().production_pipeline("pilot", _context())

    assert report.planning_only is True
    assert report.project.page_count == 1
    assert report.stage.stage_started is False
    assert report.stage.stage_completed is False
    assert report.stage.transition_requested is False
    assert report.milestone.completed is False
    assert report.deliverable.artifact_created is False
    assert report.summary.workflow_changed is False
    assert report.summary.automatic_action_taken is False


def test_production_project_rejects_any_scope_other_than_exactly_one_page() -> None:
    with pytest.raises(ValidationError):
        ProductionProjectDTO(
            project_id="pilot",
            page_reference="pilot-1",
            current_state=PageState.DRAFT,
            page_count=2,
        )


def test_asset_management_foundation_uses_context_evidence_without_asset_mutation() -> None:
    report = V43ProductionFoundationService().asset_management("pilot", _context())

    assert report.planning_only is True
    assert report.asset.asset_created is False
    assert report.asset.asset_persisted is False
    assert report.version.version_created is False
    assert report.version.version_replaced is False
    assert report.metadata.metadata_keys == ("provenance",)
    assert report.metadata.metadata_changed is False
    assert report.dependency.dependency_references == ("storyboard",)
    assert report.dependency.dependency_resolved is False
    assert report.summary.catalog_persisted is False
    assert report.summary.distribution_enabled is False


def test_project_workspace_foundation_cannot_assign_dispatch_or_change_membership() -> None:
    report = V43ProductionFoundationService().project_workspace("pilot", _context())

    assert report.planning_only is True
    assert report.workspace.workspace_created is False
    assert report.team_member.role == "human_owner"
    assert report.team_member.membership_changed is False
    assert report.team_member.permission_granted is False
    assert report.task.assigned is False
    assert report.task.dispatched is False
    assert report.task.completed is False
    assert report.board.board_changed is False
    assert report.summary.automatic_action_taken is False


def test_deliverable_foundation_cannot_export_publish_or_distribute() -> None:
    report = V43ProductionFoundationService().deliverables("pilot", _context())

    assert report.planning_only is True
    assert report.package.package_created is False
    assert report.export_profile.export_enabled is False
    assert report.export_profile.export_performed is False
    assert report.artifact.artifact_created is False
    assert report.artifact.artifact_uploaded is False
    assert report.release_candidate.approved is False
    assert report.release_candidate.published is False
    assert report.release_candidate.distribution_started is False
    assert report.summary.automatic_action_taken is False


def test_v4_3_foundation_keeps_delivery_and_repository_boundaries_out_of_module() -> None:
    source = (ROOT / "src/manga_director/production/v4_3_production_foundation.py").read_text(
        encoding="utf-8"
    )

    assert "manga_director.api" not in source
    assert "manga_director.cli" not in source
    assert "manga_director.mcp" not in source
    assert "manga_director.repositories" not in source
    assert "save(" not in source
    assert ".execute(" not in source
    assert "workflow_engine" not in source


def test_v4_3_foundation_docs_examples_benchmarks_and_report_are_available() -> None:
    assets = (
        "docs/PRODUCTION_PIPELINE_FOUNDATION.md",
        "docs/ASSET_MANANAGEMENT_FOUNDATION.md",
        "docs/ASSET_MANAGEMENT_FOUNDATION.md",
        "docs/PROJECT_WORKSPACE.md",
        "docs/DELIVERABLE_MANAGEMENT.md",
        "docs/V4_3_ITERATION_1_PRODUCTION_FOUNDATION_REPORT.md",
        "examples/production_pipeline/v4_3_foundation.py",
        "examples/asset_catalog/v4_3_foundation.py",
        "examples/project_workspace/v4_3_foundation.py",
        "examples/deliverables/v4_3_foundation.py",
        "benchmarks/production_pipeline_v4_3.py",
        "benchmarks/asset_management_v4_3.py",
        "benchmarks/workspace_v4_3.py",
        "benchmarks/deliverables_v4_3.py",
    )

    assert all((ROOT / asset).is_file() for asset in assets)


def test_v4_3_foundation_quality_gates_and_technical_debt_are_registered() -> None:
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    for gate in (
        "Production Pipeline Validation",
        "Asset Management Validation",
        "Workspace Validation",
        "Deliverable Validation",
    ):
        assert gate in gates
    for category in (
        "Production Pipeline",
        "Asset Management",
        "Project Workspace",
        "Deliverable Management",
    ):
        assert category in debt
