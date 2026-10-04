"""Contracts for v4.3 non-executing production operations DTOs."""

from __future__ import annotations

from pathlib import Path

from manga_director.domain.state_machine import PageState
from manga_director.production import V43ProductionOperationsService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}},
    )


def test_production_governance_cannot_enforce_policy_or_grant_approval() -> None:
    report = V43ProductionOperationsService().production_governance("pilot", _context())

    assert report.planning_only is True
    assert report.policy.state_machine_authoritative is True
    assert report.policy.policy_enforced is False
    assert report.policy.policy_persisted is False
    assert report.compliance.page_count == 1
    assert report.compliance.compliance_confirmed is False
    assert report.compliance.workflow_changed is False
    assert report.approval_matrix.approval_granted is False
    assert report.approval_matrix.automatic_approval_enabled is False
    assert report.summary.enforcement_action_taken is False


def test_quality_assurance_cannot_evaluate_remediate_or_approve() -> None:
    report = V43ProductionOperationsService().quality_assurance("pilot", _context())

    assert report.planning_only is True
    assert report.session.session_started is False
    assert report.rule.rule_evaluated is False
    assert report.rule.remediation_applied is False
    assert report.checklist.checklist_completed is False
    assert report.checklist.approval_granted is False
    assert report.score.score == 0
    assert report.score.quality_gate_passed is False
    assert report.summary.automatic_action_taken is False


def test_operations_monitoring_cannot_monitor_send_alerts_or_remediate() -> None:
    report = V43ProductionOperationsService().operations_monitoring("pilot", _context())

    assert report.planning_only is True
    assert report.metrics.metric_persisted is False
    assert report.metrics.telemetry_export_enabled is False
    assert report.timeline.monitoring_active is False
    assert report.alert.alert_configured is False
    assert report.alert.alert_sent is False
    assert report.alert.remediation_triggered is False
    assert report.dashboard.automatic_action_taken is False
    assert report.summary.automatic_action_taken is False


def test_platform_reliability_cannot_check_detect_recover_or_remediate() -> None:
    report = V43ProductionOperationsService().platform_reliability("pilot", _context())

    assert report.planning_only is True
    assert report.health.check_executed is False
    assert report.incident.detected is False
    assert report.incident.escalation_sent is False
    assert report.recovery_policy.automatic_retry_enabled is False
    assert report.recovery_policy.automatic_recovery_enabled is False
    assert report.recovery_policy.policy_enforced is False
    assert report.metrics.remediation_applied is False
    assert report.summary.automatic_action_taken is False


def test_v4_3_operations_keep_delivery_and_repository_boundaries_out_of_module() -> None:
    source = (ROOT / "src/manga_director/production/v4_3_production_operations.py").read_text(
        encoding="utf-8"
    )

    assert "manga_director.api" not in source
    assert "manga_director.cli" not in source
    assert "manga_director.mcp" not in source
    assert "manga_director.repositories" not in source
    assert "save(" not in source
    assert ".execute(" not in source
    assert "workflow_engine" not in source


def test_v4_3_operations_docs_examples_benchmarks_and_report_are_available() -> None:
    assets = (
        "docs/PRODUCTION_GOVERNANCE.md",
        "docs/QUALITY_ASSURANCE.md",
        "docs/OPERATIONS_MONITORING.md",
        "docs/PLATFORM_RELIABILITY.md",
        "docs/V4_3_ITERATION_3_PRODUCTION_OPERATIONS_REPORT.md",
        "examples/governance/v4_3_operations.py",
        "examples/quality_assurance/v4_3_operations.py",
        "examples/operations_monitoring/v4_3_operations.py",
        "examples/platform_reliability/v4_3_operations.py",
        "benchmarks/governance_v4_3.py",
        "benchmarks/quality_v4_3.py",
        "benchmarks/monitoring_v4_3.py",
        "benchmarks/reliability_v4_3.py",
    )

    assert all((ROOT / asset).is_file() for asset in assets)


def test_v4_3_operations_quality_gates_and_technical_debt_are_registered() -> None:
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    for gate in (
        "Production Governance Validation",
        "Quality Assurance Validation",
        "Operations Monitoring Validation",
        "Platform Reliability Validation",
    ):
        assert gate in gates
    for category in (
        "Production Governance",
        "Quality Assurance",
        "Operations Monitoring",
        "Platform Reliability",
    ):
        assert category in debt
