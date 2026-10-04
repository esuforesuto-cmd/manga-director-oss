"""Contracts for non-executing v4.4 Enterprise Creative Platform foundations."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.domain.state_machine import PageState
from manga_director.production import V44EnterpriseFoundationService, V44MarketplaceEntryDTO
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}},
        metadata={"provenance": "human"},
    )


def test_enterprise_workspace_foundation_is_one_page_and_cannot_change_workflow() -> None:
    report = V44EnterpriseFoundationService().enterprise_workspace("pilot", _context())

    assert report.planning_only is True
    assert report.workspace.page_count == 1
    assert report.workspace.workspace_created is False
    assert report.workspace.workspace_persisted is False
    assert report.session.session_started is False
    assert report.snapshot.snapshot_captured is False
    assert report.summary.workflow_changed is False
    assert report.summary.automatic_action_taken is False


def test_team_foundation_cannot_change_membership_assign_or_approve() -> None:
    report = V44EnterpriseFoundationService().team("pilot", _context())

    assert report.planning_only is True
    assert report.team.team_created is False
    assert report.member.role == "human_owner"
    assert report.member.membership_changed is False
    assert report.member.permission_granted is False
    assert report.review.storyboard_required is True
    assert report.review.completed_quality_review_required is True
    assert report.review.assigned is False
    assert report.review.approval_granted is False


def test_portfolio_foundation_observes_one_project_without_allocation_or_schedule_change() -> None:
    report = V44EnterpriseFoundationService().portfolio("pilot", _context())

    assert report.planning_only is True
    assert report.portfolio.project_ids == ("pilot",)
    assert report.portfolio.project_count == 1
    assert report.portfolio.portfolio_persisted is False
    assert report.project.health == "observed"
    assert report.project.project_changed is False
    assert report.summary.capacity_allocated is False
    assert report.summary.schedule_changed is False


def test_extension_registry_foundation_cannot_discover_load_execute_or_grant_permission() -> None:
    report = V44EnterpriseFoundationService().extension_registry("pilot", _context())

    assert report.planning_only is True
    assert report.manifest.extension_loaded is False
    assert report.manifest.extension_executed is False
    assert report.compatibility.extension_sdk_contract == "existing_sdk_unchanged"
    assert report.compatibility.permission_granted is False
    assert report.registry.registry_persisted is False
    assert report.registry.remote_discovery_enabled is False
    assert report.summary.automatic_action_taken is False


def test_marketplace_catalog_foundation_is_one_page_and_cannot_install_execute_publish_or_bill() -> None:
    report = V44EnterpriseFoundationService().marketplace_catalog("pilot", _context())

    assert report.planning_only is True
    assert report.catalog.catalog_persisted is False
    assert report.catalog.remote_discovery_enabled is False
    assert report.entry.page_count == 1
    assert report.entry.downloaded is False
    assert report.entry.installed is False
    assert report.entry.executed is False
    assert report.entry.published is False
    assert report.policy.human_review_required is True
    assert report.policy.policy_enforced is False
    assert report.policy.payment_processed is False
    assert report.policy.billing_performed is False


def test_marketplace_entry_rejects_more_than_one_page_scope() -> None:
    with pytest.raises(ValidationError):
        V44MarketplaceEntryDTO(entry_id="entry", workflow_id="workflow", page_count=2)


def test_v4_4_foundation_keeps_delivery_repository_and_extension_execution_boundaries_out_of_module() -> None:
    source = (ROOT / "src/manga_director/production/v4_4_enterprise_foundation.py").read_text(
        encoding="utf-8"
    )

    assert "manga_director.api" not in source
    assert "manga_director.cli" not in source
    assert "manga_director.mcp" not in source
    assert "manga_director.repositories" not in source
    assert "save(" not in source
    assert ".execute(" not in source
    assert "workflow_engine" not in source


def test_v4_4_foundation_docs_report_quality_gates_and_debt_are_available() -> None:
    assets = (
        "docs/ENTERPRISE_WORKSPACE_FOUNDATION.md",
        "docs/TEAM_FOUNDATION.md",
        "docs/PORTFOLIO_FOUNDATION.md",
        "docs/EXTENSION_REGISTRY.md",
        "docs/MARKETPLACE_FOUNDATION.md",
        "docs/V4_4_ITERATION_1_FOUNDATION_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    for gate in (
        "Enterprise Workspace Foundation Validation",
        "Team Foundation Validation",
        "Portfolio Foundation Validation",
        "Extension Registry Foundation Validation",
        "Marketplace Catalog Foundation Validation",
    ):
        assert gate in gates
    for category in (
        "Enterprise Workspace",
        "Team Foundation",
        "Portfolio Foundation",
        "Extension Registry",
        "Marketplace Catalog",
    ):
        assert category in debt
