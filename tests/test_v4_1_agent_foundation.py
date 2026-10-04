"""Contracts for the non-executing v4.1 agent foundation."""

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
    V41AgentFoundationService,
)
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _service() -> V41AgentFoundationService:
    role = RoleDTO(
        role_id="editor",
        name="Editor",
        responsibilities=("prepare human review evidence",),
    )
    capability = CapabilityDTO(
        capability_id="review-preparation",
        name="Review preparation",
        description="Prepares a non-executing review request.",
    )
    editor = AgentDTO(
        agent_id="editor-1",
        profile=AgentProfileDTO(
            profile_id="editor-profile",
            display_name="Editor foundation profile",
            role=role,
            capabilities=(capability,),
        ),
    )
    reviewer = AgentDTO(
        agent_id="reviewer-1",
        profile=AgentProfileDTO(
            profile_id="reviewer-profile",
            display_name="Reviewer foundation profile",
            role=role,
        ),
    )
    return V41AgentFoundationService(AgentRegistryRepository((editor, reviewer)))


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}},
    )


def test_agent_registry_is_immutable_and_does_not_change_project_repository_contract() -> None:
    service = _service()

    snapshot = service.registry()

    assert tuple(agent.agent_id for agent in snapshot.agents) == ("editor-1", "reviewer-1")
    assert snapshot.registry_persisted is False
    assert snapshot.repository_contract_changed is False
    assert all(agent.execution_enabled is False for agent in snapshot.agents)


def test_agent_registry_rejects_duplicate_ids() -> None:
    role = RoleDTO(role_id="role", name="Role")
    agent = AgentDTO(
        agent_id="duplicate",
        profile=AgentProfileDTO(profile_id="profile", display_name="A", role=role),
    )

    with pytest.raises(ValueError, match="unique"):
        AgentRegistryRepository((agent, agent))


def test_agent_runtime_prepares_a_request_but_never_executes_or_changes_workflow() -> None:
    report = _service().runtime("editor-1", "pilot", _context())

    assert report.planning_only is True
    assert report.session.session_started is False
    assert report.session.long_running is False
    assert report.session.context.multiple_pages_requested is False
    assert report.state.self_improvement_enabled is False
    assert report.request.execution_enabled is False
    assert report.request.requires_human_review is True
    assert report.result.executed is False
    assert report.result.workflow_changed is False
    assert report.result.automatic_action_taken is False


def test_collaboration_is_single_page_diagnostic_without_assignment_or_approval() -> None:
    report = _service().collaboration("editor-1", "pilot", _context())

    assert report.planning_only is True
    assert report.shared_context.page_reference == "pilot-1"
    assert report.task.execution_enabled is False
    assert report.assignment.accepted is False
    assert report.assignment.assignment_persisted is False
    assert report.review.completed is False
    assert report.review.approval_granted is False
    assert report.summary.automatic_action_taken is False


def test_communication_creates_no_transport_or_persistent_log() -> None:
    report = _service().communication("editor-1", "reviewer-1", "pilot", _context())

    assert report.planning_only is True
    assert report.log.channel.transport_connected is False
    assert report.log.channel.channel_persisted is False
    assert report.log.log_persisted is False
    assert report.log.messages[0].network_sent is False
    assert report.log.messages[0].message_persisted is False
    assert report.log.events[0].event_persisted is False
    assert report.summary.delivered_message_count == 0


def test_agent_foundation_docs_examples_benchmarks_and_report_are_available() -> None:
    assets = (
        "docs/AGENT_REGISTRY.md",
        "docs/AGENT_RUNTIME.md",
        "docs/COLLABORATION_FOUNDATION.md",
        "docs/AGENT_COMMUNICATION.md",
        "docs/V4_1_ITERATION_1_AGENT_FOUNDATION_REPORT.md",
        "examples/agent_registry/v4_1_foundation.py",
        "examples/runtime/v4_1_foundation.py",
        "examples/collaboration/v4_1_foundation.py",
        "examples/communication/v4_1_foundation.py",
        "benchmarks/agent_registry_v4_1.py",
        "benchmarks/agent_runtime_v4_1.py",
        "benchmarks/agent_collaboration_v4_1.py",
        "benchmarks/agent_messaging_v4_1.py",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
