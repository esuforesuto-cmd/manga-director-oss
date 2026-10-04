"""Contracts for non-enforcing v4.4 enterprise governance and reliability."""

from __future__ import annotations

from pathlib import Path

from manga_director.domain.project import Chapter, Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production import V44EnterpriseGovernanceService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}},
        metadata={"provenance": "human"},
    )


def _repository() -> InMemoryRepository:
    repository = InMemoryRepository()
    repository.save(
        Project(
            id="pilot",
            title="Pilot",
            chapters=[Chapter(id="one", title="One", page_numbers=[1])],
            pages=[Page(page_number=1, storyboard={"panels": []})],
        )
    )
    return repository


def test_enterprise_governance_is_advisory_and_retains_state_machine_authority() -> None:
    report = V44EnterpriseGovernanceService().enterprise_governance("pilot", _context())

    assert report.planning_only is True
    assert report.policy.state_machine_authoritative is True
    assert report.policy.human_approval_required is True
    assert report.policy.policy_enforced is False
    assert report.compliance.page_count == 1
    assert report.compliance.storyboard_evidence_required is True
    assert report.compliance.completed_quality_review_required is True
    assert report.compliance.compliance_confirmed is False
    assert report.compliance.membership_changed is False
    assert report.compliance.workflow_changed is False
    assert report.summary.automatic_action_taken is False


def test_workspace_compliance_cannot_confirm_or_change_membership_or_workflow() -> None:
    compliance = V44EnterpriseGovernanceService().workspace_compliance("pilot", _context())

    assert compliance.compliance_confirmed is False
    assert compliance.membership_changed is False
    assert compliance.workflow_changed is False


def test_portfolio_governance_cannot_enforce_allocate_schedule_or_remediate() -> None:
    report = V44EnterpriseGovernanceService().portfolio_governance("pilot", _context())

    assert report.planning_only is True
    assert report.policy.human_review_required is True
    assert report.policy.policy_enforced is False
    assert report.compliance.compliance_confirmed is False
    assert report.compliance.capacity_allocated is False
    assert report.compliance.schedule_changed is False
    assert report.compliance.remediation_applied is False


def test_marketplace_governance_cannot_enforce_approve_publish_pay_or_bill() -> None:
    report = V44EnterpriseGovernanceService().marketplace_governance("pilot", _context())

    assert report.planning_only is True
    assert report.governance.human_review_required is True
    assert report.governance.provenance_reviewed is False
    assert report.governance.compatibility_confirmed is False
    assert report.governance.policy_enforced is False
    assert report.governance.publication_approved is False
    assert report.governance.payment_approved is False
    assert report.governance.billing_approved is False


def test_enterprise_reliability_is_diagnostic_only_without_monitoring_or_recovery() -> None:
    report = V44EnterpriseGovernanceService().enterprise_reliability("pilot", _context())

    assert report.planning_only is True
    assert report.reliability.health_status == "not_checked"
    assert report.reliability.health_check_executed is False
    assert report.reliability.incident_detected is False
    assert report.reliability.monitoring_active is False
    assert report.reliability.alert_sent is False
    assert report.reliability.recovery_attempted is False
    assert report.reliability.recovery_completed is False
    assert report.summary.automatic_action_taken is False


def test_enterprise_integration_and_end_to_end_validation_preserve_save_reload_and_boundaries() -> None:
    repository = _repository()
    report = V44EnterpriseGovernanceService().operations_validation("pilot", _context())
    reloaded = repository.load("pilot")

    assert report.planning_only is True
    assert report.end_to_end_validated is True
    assert report.workflow_executed is False
    assert report.governance.compliance.workflow_changed is False
    assert report.portfolio.compliance.capacity_allocated is False
    assert report.marketplace.governance.publication_approved is False
    assert report.reliability.reliability.recovery_completed is False
    assert reloaded.pages[0].storyboard == {"panels": []}


def test_v4_4_governance_keeps_delivery_repository_and_runtime_boundaries_out_of_module() -> None:
    source = (ROOT / "src/manga_director/production/v4_4_enterprise_governance.py").read_text(
        encoding="utf-8"
    )

    assert "manga_director.api" not in source
    assert "manga_director.cli" not in source
    assert "manga_director.mcp" not in source
    assert "manga_director.repositories" not in source
    assert "save(" not in source
    assert ".execute(" not in source
    assert "workflow_engine" not in source


def test_v4_4_governance_docs_report_quality_gates_and_debt_are_available() -> None:
    assets = (
        "docs/ENTERPRISE_GOVERNANCE.md",
        "docs/WORKSPACE_COMPLIANCE.md",
        "docs/PORTFOLIO_GOVERNANCE.md",
        "docs/MARKETPLACE_GOVERNANCE.md",
        "docs/ENTERPRISE_RELIABILITY.md",
        "docs/V4_4_ITERATION_3_ENTERPRISE_GOVERNANCE_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    for gate in (
        "Enterprise Governance Validation",
        "Workspace Compliance Validation",
        "Portfolio Governance Validation",
        "Marketplace Governance Validation",
        "Enterprise Reliability Validation",
        "Enterprise End-to-End Validation",
    ):
        assert gate in gates
    for category in (
        "Enterprise Governance",
        "Workspace Compliance",
        "Portfolio Governance",
        "Marketplace Governance",
        "Enterprise Reliability",
    ):
        assert category in debt
