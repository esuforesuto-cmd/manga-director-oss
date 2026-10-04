"""Contracts for the v4.2 non-executing autonomous workflow projections."""

from __future__ import annotations

from pathlib import Path

from manga_director.domain.state_machine import PageState
from manga_director.production import V42AutonomousWorkflowService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context(*, storyboard: bool = True) -> WorkflowContext:
    page = {"id": "pilot-1"}
    artifacts = {}
    if storyboard:
        page["storyboard"] = {"panels": []}
        artifacts["storyboard"] = {"panels": []}
    return WorkflowContext(page=page, state=PageState.PROMPT_BUILT, artifacts=artifacts)


def test_goal_management_is_one_page_human_owned_and_non_authoritative() -> None:
    report = V42AutonomousWorkflowService().goal_management(
        "pilot", _context(), "Prepare a page for human review"
    )

    assert report.planning_only is True
    assert report.manager.goal.page_count == 1
    assert report.manager.goal.human_approved is False
    assert report.manager.goal.execution_enabled is False
    assert report.manager.goal_registered is False
    assert report.manager.automatic_goal_selection_enabled is False
    assert report.hierarchy.multi_page_scope_allowed is False
    assert report.milestone.completed is False
    assert report.progress.automatic_action_recommended is False
    assert report.summary.autonomous_decision_enabled is False


def test_adaptive_planning_cannot_apply_revision_prioritize_or_resolve_automatically() -> None:
    report = V42AutonomousWorkflowService().adaptive_planning(
        "pilot", _context(), "Prepare a page for human review"
    )

    assert report.planning_only is True
    assert report.session.session_started is False
    assert report.session.session_persisted is False
    assert report.revision.revision_applied is False
    assert report.revision.workflow_changed is False
    assert report.prioritization.automatic_prioritization_enabled is False
    assert report.dependency_resolver.resolution_required is True
    assert report.dependency_resolver.resolution_applied is False
    assert report.dependency_resolver.state_machine_bypassed is False
    assert report.automatic_action_taken is False


def test_pipeline_automation_is_a_human_approved_not_run_projection() -> None:
    report = V42AutonomousWorkflowService().pipeline_automation("pilot", _context())

    assert report.planning_only is True
    assert report.definition.execution_enabled is False
    assert report.definition.pipeline_persisted is False
    assert report.stage.state_machine_revalidation_required is True
    assert report.stage.stage_started is False
    assert report.stage.stage_completed is False
    assert report.stage_result.result_status == "not_run"
    assert report.stage_result.artifact_created is False
    assert report.rule.requires_human_approval is True
    assert report.rule.rule_enforced is False
    assert report.rule.automatic_dispatch_enabled is False
    assert report.summary.automatic_action_taken is False


def test_execution_recovery_only_diagnoses_and_recommends_human_review() -> None:
    report = V42AutonomousWorkflowService().execution_recovery("pilot", _context(storyboard=False))

    assert report.planning_only is True
    assert report.failure.failure_detected is True
    assert report.failure.reason == "missing_storyboard_evidence"
    assert report.failure.monitoring_active is False
    assert report.plan.recommended_action == "human_review"
    assert report.plan.recovery_execution_enabled is False
    assert report.retry.max_automatic_attempts == 0
    assert report.retry.retry_performed is False
    assert report.result.recovered is False
    assert report.result.state_restored is False
    assert report.result.workflow_changed is False
    assert report.summary.automatic_action_taken is False


def test_v4_2_iteration_2_docs_examples_benchmarks_and_report_are_available() -> None:
    assets = (
        "docs/GOAL_MANAGEMENT.md",
        "docs/ADAPTIVE_PLANNING.md",
        "docs/PIPELINE_AUTOMATION.md",
        "docs/EXECUTION_RECOVERY.md",
        "docs/V4_2_ITERATION_2_AUTONOMOUS_WORKFLOW_REPORT.md",
        "examples/goal_management/v4_2_iteration_2.py",
        "examples/adaptive_planning/v4_2_iteration_2.py",
        "examples/pipeline_automation/v4_2_iteration_2.py",
        "examples/execution_recovery/v4_2_iteration_2.py",
        "benchmarks/goal_management_v4_2.py",
        "benchmarks/planning_v4_2.py",
        "benchmarks/pipeline_v4_2.py",
        "benchmarks/recovery_v4_2.py",
    )

    assert all((ROOT / asset).is_file() for asset in assets)


def test_v4_2_iteration_2_quality_gates_and_technical_debt_are_registered() -> None:
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    for gate in (
        "Goal Management Validation",
        "Adaptive Planning Validation",
        "Pipeline Automation Validation",
        "Execution Recovery Validation",
    ):
        assert gate in gates
    for category in (
        "Goal Management",
        "Adaptive Planning",
        "Pipeline Automation",
        "Execution Recovery",
    ):
        assert category in debt
