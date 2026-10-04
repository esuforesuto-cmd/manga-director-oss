"""Contracts for v4.2 human-governed autonomous operations projections."""

from __future__ import annotations

from pathlib import Path

from manga_director.domain.state_machine import PageState
from manga_director.production import V42AutonomousOperationsService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context(*, storyboard: bool = True) -> WorkflowContext:
    page: dict[str, object] = {"id": "pilot-1"}
    artifacts: dict[str, object] = {}
    if storyboard:
        page["storyboard"] = {"panels": []}
        artifacts["storyboard"] = {"panels": []}
    return WorkflowContext(page=page, state=PageState.PROMPT_BUILT, artifacts=artifacts)


def test_human_supervision_cannot_approve_intervene_or_bypass_state_machine() -> None:
    report = V42AutonomousOperationsService().human_supervision("pilot", _context())

    assert report.planning_only is True
    assert report.session.session_started is False
    assert report.approval_checkpoint.approval_requested is False
    assert report.approval_checkpoint.approval_granted is False
    assert report.approval_checkpoint.storyboard_evidence_required is True
    assert report.approval_checkpoint.quality_review_required is True
    assert report.intervention.intervention_applied is False
    assert report.intervention.workflow_changed is False
    assert report.override_request.human_authorization_required is True
    assert report.override_request.override_granted is False
    assert report.override_request.state_machine_bypassed is False


def test_execution_governance_is_advisory_and_identifies_missing_storyboard_risk() -> None:
    report = V42AutonomousOperationsService().execution_governance("pilot", _context(storyboard=False))

    assert report.planning_only is True
    assert report.policy.enforcement_enabled is False
    assert report.risk.risk_level == "high"
    assert report.risk.requires_human_review is True
    assert report.risk.risk_accepted is False
    assert report.safety_boundary.exactly_one_page_required is True
    assert report.safety_boundary.state_machine_authoritative is True
    assert report.safety_boundary.persisted_storyboard_required is True
    assert report.safety_boundary.completed_quality_review_required is True
    assert report.safety_boundary.boundary_enforced is False
    assert report.compliance.compliance_confirmed is False
    assert report.summary.automatic_action_taken is False


def test_observability_is_local_without_monitoring_telemetry_or_events() -> None:
    report = V42AutonomousOperationsService().observability("pilot", _context())

    assert report.planning_only is True
    assert report.metrics.executing_session_count == 0
    assert report.metrics.metric_collection_active is False
    assert report.metrics.metrics_persisted is False
    assert report.trace.span_count == 0
    assert report.trace.trace_recorded is False
    assert report.trace.remote_export_enabled is False
    assert report.event.event_persisted is False
    assert report.event.event_published is False
    assert report.dashboard.monitoring_active is False
    assert report.dashboard.alerting_enabled is False
    assert report.summary.automatic_action_taken is False


def test_reliability_cannot_monitor_retry_recover_or_remediate() -> None:
    report = V42AutonomousOperationsService().reliability("pilot", _context(storyboard=False))

    assert report.planning_only is True
    assert report.failure.category == "evidence_missing"
    assert report.failure.failure_detected is True
    assert report.failure.automatic_remediation_enabled is False
    assert report.recovery_workflow.recommended_action == "human_review"
    assert report.recovery_workflow.recovery_started is False
    assert report.recovery_workflow.recovery_completed is False
    assert report.retry_policy.max_automatic_attempts == 0
    assert report.retry_policy.retry_performed is False
    assert report.health.health_check_performed is False
    assert report.health.remediation_applied is False
    assert report.dashboard.monitoring_active is False
    assert report.dashboard.retry_execution_enabled is False
    assert report.dashboard.recovery_execution_enabled is False


def test_autonomous_operations_integration_remains_human_governed_and_nonexecuting() -> None:
    report = V42AutonomousOperationsService().operations("pilot", _context(storyboard=False))

    assert report.planning_only is True
    assert report.supervision.approval_checkpoint.approval_granted is False
    assert report.governance.policy.enforcement_enabled is False
    assert report.observability.dashboard.monitoring_active is False
    assert report.reliability.recovery_workflow.recovery_started is False


def test_v4_2_iteration_3_docs_examples_benchmarks_and_report_are_available() -> None:
    assets = (
        "docs/HUMAN_SUPERVISION.md",
        "docs/EXECUTION_GOVERNANCE.md",
        "docs/EXECUTION_OBSERVABILITY.md",
        "docs/EXECUTION_RELIABILITY.md",
        "docs/V4_2_ITERATION_3_AUTONOMOUS_OPERATIONS_REPORT.md",
        "examples/supervision/v4_2_iteration_3.py",
        "examples/governance/v4_2_iteration_3.py",
        "examples/observability/v4_2_iteration_3.py",
        "examples/reliability/v4_2_iteration_3.py",
        "benchmarks/supervision_v4_2.py",
        "benchmarks/governance_v4_2.py",
        "benchmarks/monitoring_v4_2.py",
        "benchmarks/reliability_v4_2.py",
    )

    assert all((ROOT / asset).is_file() for asset in assets)


def test_v4_2_iteration_3_quality_gates_and_technical_debt_are_registered() -> None:
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    for gate in (
        "Human Supervision Validation",
        "Execution Governance Validation",
        "Observability Validation",
        "Reliability Validation",
    ):
        assert gate in gates
    for category in (
        "Human Supervision",
        "Execution Governance",
        "Observability",
        "Reliability",
    ):
        assert category in debt
