"""Contracts for v4.1 orchestration, planning, collaboration, and conflict DTOs."""

from __future__ import annotations

from pathlib import Path

import pytest

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_1_agent_foundation import (
    AgentDTO,
    AgentProfileDTO,
    AgentRegistryRepository,
    RoleDTO,
)
from manga_director.production.v4_1_orchestration import V41OrchestrationService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _service() -> V41OrchestrationService:
    role = RoleDTO(role_id="creative", name="Creative")
    agents = tuple(
        AgentDTO(
            agent_id=agent_id,
            profile=AgentProfileDTO(
                profile_id=f"{agent_id}-profile", display_name=agent_id, role=role
            ),
        )
        for agent_id in ("editor-1", "reviewer-1")
    )
    return V41OrchestrationService(AgentRegistryRepository(agents))


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}},
    )


def test_orchestration_is_one_page_plan_without_dispatch_or_transition() -> None:
    report = _service().orchestration("pilot", _context())

    assert report.planning_only is True
    assert report.orchestration.page_reference == "pilot-1"
    assert report.orchestration.autonomous_decision_enabled is False
    assert report.plan.execution_enabled is False
    assert report.plan.manual_execution_required is True
    assert report.queue.queued_for_dispatch is False
    assert report.queue.queue_persisted is False
    assert report.plan.dependencies[0].workflow_transition_requested is False
    assert report.summary.dispatched_task_count == 0
    assert report.summary.workflow_changed is False


def test_planning_engine_creates_only_human_reviewed_disabled_tasks() -> None:
    report = _service().planning("pilot", _context())

    assert report.planning_only is True
    assert report.request.page_reference == "pilot-1"
    assert report.request.request_persisted is False
    assert report.priority.automatic_prioritization_enabled is False
    assert all(task.requires_human_review for task in report.result.tasks)
    assert all(task.executable is False for task in report.result.tasks)
    assert report.result.workflow_changed is False
    assert report.summary.execution_enabled is False
    assert report.summary.self_learning_enabled is False


def test_collaboration_workflow_cannot_accept_assignments_or_complete_review_or_approval() -> None:
    report = _service().collaboration_workflow("editor-1", "reviewer-1", "pilot", _context())

    assert report.planning_only is True
    assert report.assignment.assignment_accepted is False
    assert report.assignment.assignment_persisted is False
    assert report.review.review_required is True
    assert report.review.quality_review_completed is False
    assert report.approval.quality_review_completed is False
    assert report.approval.approval_granted is False
    assert report.approval.state_machine_bypassed is False
    assert report.handoff.handoff_performed is False
    assert report.automatic_action_taken is False


def test_collaboration_workflow_rejects_unknown_agents() -> None:
    with pytest.raises(ValueError, match="unknown agent"):
        _service().collaboration_workflow("missing", "reviewer-1", "pilot", _context())


def test_conflict_resolution_is_advisory_and_cannot_merge_or_record_a_decision() -> None:
    report = _service().conflict_resolution("pilot", _context())

    assert report.planning_only is True
    assert report.conflict.detected is False
    assert report.strategy.automatic_resolution_enabled is False
    assert report.merge.merge_applied is False
    assert report.merge.content_changed is False
    assert report.decision.decision_recorded is False
    assert report.decision.human_decision_required is True
    assert report.summary.resolved_conflict_count == 0
    assert report.summary.automatic_action_taken is False


def test_orchestration_docs_examples_benchmarks_and_report_are_available() -> None:
    assets = (
        "docs/ORCHESTRATION_ENGINE.md",
        "docs/TASK_PLANNING.md",
        "docs/COLLABORATION_WORKFLOW.md",
        "docs/CONFLICT_RESOLUTION.md",
        "docs/V4_1_ITERATION_2_ORCHESTRATION_REPORT.md",
        "examples/orchestration/v4_1_iteration_2.py",
        "examples/planning/v4_1_iteration_2.py",
        "examples/collaboration_workflow/v4_1_iteration_2.py",
        "examples/conflict_resolution/v4_1_iteration_2.py",
        "benchmarks/orchestration_v4_1.py",
        "benchmarks/planning_v4_1.py",
        "benchmarks/collaboration_workflow_v4_1.py",
        "benchmarks/conflict_resolution_v4_1.py",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
