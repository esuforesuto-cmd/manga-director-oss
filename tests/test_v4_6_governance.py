"""Contracts for non-enforcing v4.6 intelligence operations reports."""

from __future__ import annotations

from pathlib import Path

from manga_director.domain.project import Chapter, Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production import V46IntelligenceGovernanceService
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


def test_intelligence_governance_is_advisory_and_retains_state_machine_authority() -> None:
    report = V46IntelligenceGovernanceService().intelligence_governance("pilot", _context())

    assert report.planning_only is True
    assert report.policy.state_machine_authoritative is True
    assert report.policy.human_review_required is True
    assert report.policy.policy_enforced is False
    assert report.policy.policy_persisted is False
    assert report.compliance.page_count == 1
    assert report.compliance.storyboard_evidence_required is True
    assert report.compliance.completed_quality_review_required is True
    assert report.compliance.compliance_confirmed is False
    assert report.compliance.autonomous_decision_made is False
    assert report.summary.automatic_action_taken is False


def test_context_governance_cannot_enforce_persist_share_or_grant_access() -> None:
    report = V46IntelligenceGovernanceService().context_governance("pilot", _context())

    assert report.planning_only is True
    assert report.policy.provenance_required is True
    assert report.policy.redaction_required is True
    assert report.policy.consent_required is True
    assert report.policy.policy_enforced is False
    assert report.policy.context_persisted is False
    assert report.compliance.page_count == 1
    assert report.compliance.provenance_confirmed is False
    assert report.compliance.redaction_confirmed is False
    assert report.compliance.consent_confirmed is False
    assert report.compliance.access_granted is False
    assert report.compliance.context_shared is False


def test_reasoning_audit_cannot_persist_update_model_or_decide() -> None:
    report = V46IntelligenceGovernanceService().reasoning_audit("pilot", _context())

    assert report.planning_only is True
    assert report.audit.page_count == 1
    assert report.audit.evidence_trace_required is True
    assert report.audit.uncertainty_explanation_required is True
    assert report.audit.audit_persisted is False
    assert report.audit.model_updated is False
    assert report.audit.autonomous_decision_made is False
    assert report.summary.audit_action_taken is False
    assert report.summary.automatic_action_taken is False


def test_workflow_observability_is_diagnostic_only_without_monitoring_or_execution() -> None:
    report = V46IntelligenceGovernanceService().workflow_observability("pilot", _context())

    assert report.planning_only is True
    assert report.observation.page_count == 1
    assert report.observation.state_machine_authoritative is True
    assert report.observation.timeline_entry_count == 0
    assert report.observation.metrics_collected is False
    assert report.observation.monitoring_active is False
    assert report.observation.workflow_executed is False
    assert report.summary.trace_available is False
    assert report.summary.alert_sent is False
    assert report.summary.operational_action_taken is False


def test_intelligence_reliability_is_diagnostic_only_without_monitoring_or_recovery() -> None:
    report = V46IntelligenceGovernanceService().intelligence_reliability("pilot", _context())

    assert report.planning_only is True
    assert report.reliability.health_status == "not_checked"
    assert report.reliability.health_check_executed is False
    assert report.reliability.failure_detected is False
    assert report.reliability.monitoring_active is False
    assert report.reliability.alert_sent is False
    assert report.reliability.retry_attempted is False
    assert report.reliability.recovery_attempted is False
    assert report.summary.automatic_action_taken is False


def test_intelligence_operations_validation_preserves_save_reload_and_boundaries() -> None:
    repository = _repository()
    report = V46IntelligenceGovernanceService().operations_validation("pilot", _context())
    reloaded = repository.load("pilot")

    assert report.planning_only is True
    assert report.end_to_end_validated is True
    assert report.workflow_executed is False
    assert report.governance.compliance.autonomous_decision_made is False
    assert report.context.compliance.context_shared is False
    assert report.reasoning.audit.model_updated is False
    assert report.workflow.observation.workflow_executed is False
    assert report.reliability.reliability.recovery_attempted is False
    assert reloaded.pages[0].storyboard == {"panels": []}


def test_v4_6_governance_keeps_delivery_repository_and_runtime_boundaries_out_of_module() -> None:
    source = (ROOT / "src/manga_director/production/v4_6_governance.py").read_text(
        encoding="utf-8"
    )

    assert "manga_director.api" not in source
    assert "manga_director.cli" not in source
    assert "manga_director.mcp" not in source
    assert "manga_director.repositories" not in source
    assert "save(" not in source
    assert ".execute(" not in source
    assert "workflow_engine" not in source


def test_v4_6_governance_docs_report_quality_gates_and_debt_are_available() -> None:
    assets = (
        "docs/INTELLIGENCE_GOVERNANCE.md",
        "docs/CONTEXT_GOVERNANCE.md",
        "docs/REASONING_AUDIT.md",
        "docs/WORKFLOW_OBSERVABILITY.md",
        "docs/INTELLIGENCE_RELIABILITY.md",
        "docs/V4_6_ITERATION_3_CREATIVE_INTELLIGENCE_GOVERNANCE_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    for gate in (
        "Intelligence Governance Validation",
        "Context Governance Validation",
        "Reasoning Audit Validation",
        "Workflow Observability Validation",
        "Intelligence Reliability Validation",
    ):
        assert gate in gates
    for category in (
        "Intelligence Governance",
        "Context Governance",
        "Reasoning Audit",
        "Workflow Observability",
        "Intelligence Reliability",
    ):
        assert category in debt
