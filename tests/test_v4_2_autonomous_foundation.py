"""Contracts for the non-executing v4.2 autonomous-system foundation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.domain.state_machine import PageState
from manga_director.production import CheckpointDTO, CheckpointRepository, GoalDTO
from manga_director.production.v4_2_autonomous_foundation import V42AutonomousFoundationService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}},
    )


def test_autonomous_execution_foundation_is_one_page_human_started_and_disabled() -> None:
    report = V42AutonomousFoundationService().execution(
        "pilot", _context(), "Prepare a page for human review"
    )

    assert report.planning_only is True
    assert report.goal.page_count == 1
    assert report.goal.human_approved is False
    assert report.goal.execution_enabled is False
    assert report.session.human_start_required is True
    assert report.session.session_started is False
    assert report.session.context.storyboard_evidence_present is True
    assert report.state.execution_started is False
    assert report.state.workflow_changed is False
    assert report.summary.automatic_action_taken is False


def test_execution_runtime_reports_missing_storyboard_without_starting_or_mutating() -> None:
    context = WorkflowContext(
        page={"id": "pilot-1"},
        state=PageState.PROMPT_BUILT,
    )
    before = context.model_dump()

    report = V42AutonomousFoundationService().execution(
        "pilot", context, "Prepare a page for human review"
    )

    assert report.session.context.storyboard_evidence_present is False
    assert report.session.session_started is False
    assert report.state.execution_started is False
    assert report.state.workflow_changed is False
    assert context.model_dump() == before


def test_goal_rejects_any_scope_other_than_exactly_one_page() -> None:
    with pytest.raises(ValidationError):
        GoalDTO(
            goal_id="goal",
            project_id="project",
            page_reference="page",
            objective="invalid multi-page scope",
            current_state=PageState.DRAFT,
            page_count=2,
        )


def test_checkpoint_management_is_immutable_and_cannot_resume_or_change_workflow() -> None:
    report = V42AutonomousFoundationService().checkpoint("pilot", _context())

    assert report.planning_only is True
    assert report.checkpoint.checkpoint_persisted is False
    assert report.snapshot.snapshot_persisted is False
    assert report.snapshot.restoration_enabled is False
    assert report.resume_request.human_authorization_required is True
    assert report.resume_request.request_dispatched is False
    assert report.resume_result.resume_authorized is False
    assert report.resume_result.resumed is False
    assert report.resume_result.workflow_changed is False
    assert report.repository_contract_changed is False


def test_checkpoint_repository_rejects_duplicate_ids_and_only_projects_local_data() -> None:
    checkpoint = CheckpointDTO(
        checkpoint_id="checkpoint",
        session_id="session",
        page_reference="page",
        workflow_state=PageState.DRAFT,
        sequence=0,
    )

    assert CheckpointRepository((checkpoint,)).get("checkpoint") == checkpoint
    with pytest.raises(ValueError, match="unique"):
        CheckpointRepository((checkpoint, checkpoint))


def test_supervisor_runtime_is_advisory_without_monitoring_or_escalation_actions() -> None:
    report = V42AutonomousFoundationService().supervisor("pilot", _context())

    assert report.planning_only is True
    assert report.session.session_started is False
    assert report.progress.monitoring_active is False
    assert report.progress.telemetry_export_enabled is False
    assert report.health.failure_detected is False
    assert report.health.remediation_applied is False
    assert report.escalation.human_decision_required is True
    assert report.escalation.escalation_sent is False
    assert report.escalation.emergency_stop_triggered is False
    assert report.automatic_action_taken is False


def test_long_running_task_foundation_cannot_schedule_start_or_continue_work() -> None:
    report = V42AutonomousFoundationService().long_running_tasks("pilot", _context())

    assert report.planning_only is True
    assert report.queue.queued_for_dispatch is False
    assert report.queue.queue_persisted is False
    assert report.scheduled_task.schedule_registered is False
    assert report.scheduled_task.execution_enabled is False
    assert report.background_task.background_started is False
    assert report.background_task.long_running is False
    assert report.progress.automatic_continuation_enabled is False
    assert report.lifecycle.scheduled_task_count == 0
    assert report.lifecycle.running_task_count == 0
    assert report.lifecycle.automatic_action_taken is False


def test_v4_2_foundation_docs_examples_benchmarks_and_report_are_available() -> None:
    assets = (
        "docs/AUTONOMOUS_EXECUTION_FOUNDATION.md",
        "docs/CHECKPOINT_MANAGEMENT.md",
        "docs/SUPERVISOR_RUNTIME.md",
        "docs/LONG_RUNNING_TASKS.md",
        "docs/V4_2_ITERATION_1_AUTONOMOUS_FOUNDATION_REPORT.md",
        "examples/autonomous_execution/v4_2_foundation.py",
        "examples/checkpoint/v4_2_foundation.py",
        "examples/supervisor_runtime/v4_2_foundation.py",
        "examples/long_running_tasks/v4_2_foundation.py",
        "benchmarks/autonomous_execution_v4_2.py",
        "benchmarks/checkpoint_v4_2.py",
        "benchmarks/supervisor_v4_2.py",
        "benchmarks/task_runtime_v4_2.py",
    )

    assert all((ROOT / asset).is_file() for asset in assets)


def test_v4_2_foundation_quality_gates_and_technical_debt_are_registered() -> None:
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    for gate in (
        "Autonomous Execution Validation",
        "Checkpoint Validation",
        "Supervisor Runtime Validation",
        "Long-running Task Validation",
    ):
        assert gate in gates
    for category in (
        "Autonomous Execution",
        "Checkpoint Management",
        "Supervisor Runtime",
        "Long-running Tasks",
    ):
        assert category in debt
