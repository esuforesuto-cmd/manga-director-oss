"""Contracts for the v4.8 Creative Operating System operations iteration."""

from __future__ import annotations

from pathlib import Path

from manga_director.domain.state_machine import PageState
from manga_director.production import V48CreativeOperatingSystemGovernanceService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}},
        metadata={"provenance": "human"},
    )


def test_platform_governance_is_one_page_scoped_and_non_enforcing() -> None:
    report = V48CreativeOperatingSystemGovernanceService().platform_governance("pilot", _context())

    assert report.planning_only is True
    assert report.policy.page_count == 1
    assert report.policy.state_machine_authoritative is True
    assert report.policy.persisted_storyboard_required is True
    assert report.policy.completed_quality_review_required is True
    assert report.policy.human_approval_required is True
    assert report.policy.policy_enforced is False
    assert report.compliance.compliance_confirmed is False
    assert report.compliance.enforcement_action_taken is False
    assert report.summary.automatic_action_taken is False


def test_service_governance_cannot_discover_invoke_route_or_enforce() -> None:
    report = V48CreativeOperatingSystemGovernanceService().service_governance("pilot", _context())

    assert report.planning_only is True
    assert report.governance.page_count == 1
    assert report.governance.contract_preservation_required is True
    assert report.governance.human_review_required is True
    assert report.governance.service_discovered is False
    assert report.governance.service_invoked is False
    assert report.governance.service_routed is False
    assert report.governance.governance_enforced is False
    assert report.summary.permission_granted is False
    assert report.summary.automatic_action_taken is False


def test_platform_observability_cannot_collect_probe_monitor_or_alert() -> None:
    report = V48CreativeOperatingSystemGovernanceService().observability("pilot", _context())

    assert report.planning_only is True
    assert report.observation.page_count == 1
    assert report.observation.explicit_evidence_required is True
    assert report.observation.telemetry_collected is False
    assert report.observation.health_probe_executed is False
    assert report.observation.monitoring_active is False
    assert report.observation.alert_sent is False
    assert report.summary.dashboard_persisted is False
    assert report.summary.dashboard_published is False
    assert report.summary.operational_action_taken is False


def test_operational_reliability_cannot_health_check_retry_recover_or_reconfigure() -> None:
    report = V48CreativeOperatingSystemGovernanceService().operational_reliability(
        "pilot", _context()
    )

    assert report.planning_only is True
    assert report.reliability.page_count == 1
    assert report.reliability.health_status == "not_checked"
    assert report.reliability.health_check_executed is False
    assert report.reliability.failure_detected is False
    assert report.reliability.retry_attempted is False
    assert report.reliability.recovery_attempted is False
    assert report.reliability.runtime_reconfigured is False
    assert report.summary.automatic_action_taken is False


def test_lifecycle_governance_is_descriptive_and_never_mutates_or_transitions() -> None:
    report = V48CreativeOperatingSystemGovernanceService().lifecycle_governance("pilot", _context())

    assert report.planning_only is True
    assert report.policy.page_count == 1
    assert report.policy.source_provenance_required is True
    assert report.policy.state_machine_authoritative is True
    assert report.policy.retention_enforced is False
    assert report.policy.lifecycle_persisted is False
    assert report.policy.state_transitioned is False
    assert report.summary.record_mutated is False
    assert report.summary.automatic_action_taken is False


def test_creative_operating_system_integrates_reports_without_operating_the_platform() -> None:
    report = V48CreativeOperatingSystemGovernanceService().creative_operating_system(
        "pilot", _context()
    )

    assert report.planning_only is True
    assert report.summary.report_count == 5
    assert report.summary.enterprise_readiness_assessed is False
    assert report.summary.oss_readiness_assessed is False
    assert report.summary.presentation_dependency is False
    assert report.summary.automatic_action_taken is False
    assert report.platform_governance.policy.policy_enforced is False
    assert report.service_governance.governance.service_invoked is False
    assert report.observability.observation.telemetry_collected is False
    assert report.reliability.reliability.recovery_attempted is False
    assert report.lifecycle_governance.policy.state_transitioned is False


def test_v4_8_operations_keep_delivery_repository_and_runtime_boundaries_out_of_module() -> None:
    source = (ROOT / "src/manga_director/production/v4_8_unified_governance.py").read_text(
        encoding="utf-8"
    )

    assert "manga_director.api" not in source
    assert "manga_director.cli" not in source
    assert "manga_director.mcp" not in source
    assert "manga_director.repositories" not in source
    assert "save(" not in source
    assert ".execute(" not in source
    assert "workflow_engine" not in source


def test_v4_8_operations_docs_report_quality_gates_and_debt_are_available() -> None:
    assets = (
        "docs/UNIFIED_PLATFORM_GOVERNANCE.md",
        "docs/SERVICE_GOVERNANCE.md",
        "docs/PLATFORM_OBSERVABILITY.md",
        "docs/OPERATIONAL_RELIABILITY.md",
        "docs/LIFECYCLE_GOVERNANCE.md",
        "docs/V4_8_ITERATION_3_CREATIVE_OPERATING_SYSTEM_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    for gate in (
        "Unified Platform Governance Validation",
        "Service Governance Validation",
        "Platform Observability Validation",
        "Operational Reliability Validation",
        "Lifecycle Governance Validation",
    ):
        assert gate in gates
    for category in (
        "Unified Platform Governance",
        "Service Governance",
        "Platform Observability",
        "Operational Reliability",
        "Lifecycle Governance",
    ):
        assert category in debt
