"""Contracts for non-enforcing v4.5 ecosystem governance and reliability."""

from __future__ import annotations

from pathlib import Path

from manga_director.domain.project import Chapter, Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production import V45EcosystemGovernanceService
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


def test_ecosystem_governance_is_advisory_and_retains_state_machine_authority() -> None:
    report = V45EcosystemGovernanceService().ecosystem_governance("pilot", _context())

    assert report.planning_only is True
    assert report.policy.state_machine_authoritative is True
    assert report.policy.human_approval_required is True
    assert report.policy.policy_enforced is False
    assert report.compliance.page_count == 1
    assert report.compliance.storyboard_evidence_required is True
    assert report.compliance.completed_quality_review_required is True
    assert report.compliance.compliance_confirmed is False
    assert report.compliance.workflow_changed is False
    assert report.summary.automatic_action_taken is False


def test_service_trust_framework_cannot_establish_trust_or_invoke_service() -> None:
    report = V45EcosystemGovernanceService().service_trust_framework("pilot", _context())

    assert report.planning_only is True
    assert report.trust.trust_level == "not_established"
    assert report.trust.provenance_reviewed is False
    assert report.trust.compatibility_confirmed is False
    assert report.trust.human_trust_required is True
    assert report.trust.service_invoked is False
    assert report.summary.trust_granted_count == 0


def test_plugin_governance_cannot_enforce_grant_permission_or_execute() -> None:
    report = V45EcosystemGovernanceService().plugin_governance("pilot", _context())

    assert report.planning_only is True
    assert report.policy.extension_sdk_contract == "existing_sdk_unchanged"
    assert report.policy.human_review_required is True
    assert report.policy.policy_enforced is False
    assert report.compliance.provenance_reviewed is False
    assert report.compliance.isolation_confirmed is False
    assert report.compliance.permission_granted is False
    assert report.compliance.plugin_executed is False


def test_knowledge_federation_governance_cannot_share_sync_or_connect() -> None:
    report = V45EcosystemGovernanceService().knowledge_federation_governance("pilot", _context())

    assert report.planning_only is True
    assert report.policy.redaction_required is True
    assert report.policy.human_consent_required is True
    assert report.policy.policy_enforced is False
    assert report.compliance.consent_confirmed is False
    assert report.compliance.sharing_approved is False
    assert report.compliance.knowledge_synchronized is False
    assert report.compliance.federation_connected is False


def test_ecosystem_reliability_is_diagnostic_only_without_monitoring_or_recovery() -> None:
    report = V45EcosystemGovernanceService().ecosystem_reliability("pilot", _context())

    assert report.planning_only is True
    assert report.reliability.health_status == "not_checked"
    assert report.reliability.health_check_executed is False
    assert report.reliability.incident_detected is False
    assert report.reliability.monitoring_active is False
    assert report.reliability.alert_sent is False
    assert report.reliability.recovery_attempted is False
    assert report.reliability.recovery_completed is False
    assert report.summary.automatic_action_taken is False


def test_ecosystem_integration_and_end_to_end_validation_preserve_save_reload_and_boundaries() -> None:
    repository = _repository()
    report = V45EcosystemGovernanceService().operations_validation("pilot", _context())
    reloaded = repository.load("pilot")

    assert report.planning_only is True
    assert report.end_to_end_validated is True
    assert report.workflow_executed is False
    assert report.governance.compliance.workflow_changed is False
    assert report.service_trust.trust.service_invoked is False
    assert report.plugin.compliance.plugin_executed is False
    assert report.knowledge_federation.compliance.federation_connected is False
    assert report.reliability.reliability.recovery_completed is False
    assert reloaded.pages[0].storyboard == {"panels": []}


def test_v4_5_governance_keeps_delivery_repository_and_runtime_boundaries_out_of_module() -> None:
    source = (ROOT / "src/manga_director/production/v4_5_ecosystem_governance.py").read_text(
        encoding="utf-8"
    )

    assert "manga_director.api" not in source
    assert "manga_director.cli" not in source
    assert "manga_director.mcp" not in source
    assert "manga_director.repositories" not in source
    assert "save(" not in source
    assert ".execute(" not in source
    assert "workflow_engine" not in source


def test_v4_5_governance_docs_report_quality_gates_and_debt_are_available() -> None:
    assets = (
        "docs/ECOSYSTEM_GOVERNANCE.md",
        "docs/SERVICE_TRUST_FRAMEWORK.md",
        "docs/PLUGIN_GOVERNANCE.md",
        "docs/KNOWLEDGE_FEDERATION_GOVERNANCE.md",
        "docs/ECOSYSTEM_RELIABILITY.md",
        "docs/V4_5_ITERATION_3_ECOSYSTEM_GOVERNANCE_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    for gate in (
        "Ecosystem Governance Validation",
        "Service Trust Framework Validation",
        "Plugin Governance Validation",
        "Knowledge Federation Governance Validation",
        "Ecosystem Reliability Validation",
        "Ecosystem Integration Validation",
    ):
        assert gate in gates
    for category in (
        "Ecosystem Governance",
        "Service Trust Framework",
        "Plugin Governance",
        "Knowledge Federation Governance",
        "Ecosystem Reliability",
    ):
        assert category in debt
