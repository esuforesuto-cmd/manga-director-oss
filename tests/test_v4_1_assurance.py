"""Contracts for the v4.1 multi-agent human-review and assurance DTOs."""

from __future__ import annotations

from pathlib import Path

import pytest

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_1_agent_foundation import (
    AgentDTO,
    AgentProfileDTO,
    AgentRegistryRepository,
    CapabilityDTO,
    RoleDTO,
)
from manga_director.production.v4_1_assurance import V41PlatformAssuranceService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _service() -> V41PlatformAssuranceService:
    agent = AgentDTO(
        agent_id="editor-1",
        profile=AgentProfileDTO(
            profile_id="editor-profile",
            display_name="Editor",
            role=RoleDTO(role_id="editor", name="Editor"),
            capabilities=(
                CapabilityDTO(
                    capability_id="review-preparation",
                    name="Review preparation",
                    description="Diagnostic-only preparation.",
                ),
            ),
        ),
    )
    return V41PlatformAssuranceService(AgentRegistryRepository((agent,)))


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}},
    )


def test_human_in_the_loop_cannot_dispatch_or_approve_or_transition() -> None:
    report = _service().human_review("pilot", _context())

    assert report.planning_only is True
    assert report.request.human_decision_required is True
    assert report.request.quality_review_completed is False
    assert report.request.request_dispatched is False
    assert report.result.approved is False
    assert report.result.state_machine_transitioned is False
    assert report.session.review_completed is False
    assert report.feedback.submitted is False
    assert report.history.history_persisted is False


def test_agent_governance_is_advisory_and_cannot_enforce_permissions() -> None:
    report = _service().governance("editor-1")

    assert report.planning_only is True
    assert report.policy.policy_persisted is False
    assert report.policy.enforcement_enabled is False
    assert report.permission.permission_granted is False
    assert report.restriction.restriction_enforced is False
    assert report.compliance.enforcement_enabled is False
    assert report.compliance.automatic_action_taken is False


def test_observability_is_local_nonexecuting_and_nonpersistent() -> None:
    report = _service().observability("pilot", _context())

    assert report.planning_only is True
    assert report.agent_metrics.executing_agent_count == 0
    assert report.agent_metrics.remote_export_enabled is False
    assert report.trace.agent_execution_observed is False
    assert report.trace.trace_persisted is False
    assert report.timeline.event_dispatch_enabled is False
    assert report.timeline.timeline_persisted is False
    assert report.dashboard.monitoring_enabled is False
    assert report.dashboard.dashboard_persisted is False


def test_reliability_is_policy_and_diagnostic_only_with_no_retry_or_recovery() -> None:
    report = _service().reliability("pilot", _context())

    assert report.planning_only is True
    assert report.retry.max_automatic_attempts == 0
    assert report.retry.retry_performed is False
    assert report.timeout.timeout_enforced is False
    assert report.timeout.cancellation_performed is False
    assert report.recovery.recovery_started is False
    assert report.failure.remediation_applied is False
    assert report.summary.automatic_action_taken is False
    assert report.summary.long_term_memory_optimized is False


def test_multi_agent_platform_integration_remains_non_authoritative() -> None:
    report = _service().platform_report("editor-1", "pilot", _context())

    assert report.planning_only is True
    assert report.automatic_action_taken is False
    assert report.human_review.result.approved is False
    assert report.governance.policy.enforcement_enabled is False
    assert report.observability.trace.agent_execution_observed is False
    assert report.reliability.recovery.recovery_completed is False


def test_assurance_docs_examples_benchmarks_and_report_are_available() -> None:
    assets = (
        "docs/HUMAN_IN_LOOP.md",
        "docs/HUMAN_IN_THE_LOOP.md",
        "docs/AGENT_GOVERNANCE.md",
        "docs/observability.md",
        "docs/RELIABILITY.md",
        "docs/V4_1_ITERATION_3_MULTI_AGENT_PLATFORM_REPORT.md",
        "examples/approval_flow/v4_1_iteration_3.py",
        "examples/governance/v4_1_iteration_3.py",
        "examples/observability/v4_1_iteration_3.py",
        "examples/reliability/v4_1_iteration_3.py",
        "benchmarks/approval_v4_1.py",
        "benchmarks/governance_v4_1.py",
        "benchmarks/observability_v4_1.py",
        "benchmarks/reliability_v4_1.py",
    )

    assert all((ROOT / asset).is_file() for asset in assets)


def test_governance_rejects_unknown_agent() -> None:
    with pytest.raises(ValueError, match="unknown agent"):
        _service().governance("missing")
