"""Contracts for non-executing v4.6 Creative Intelligence OS foundations."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.domain.state_machine import PageState
from manga_director.production import (
    V46IntelligenceFoundationService,
    V46UnifiedCreativeContextDTO,
)
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}},
        metadata={"provenance": "human"},
    )


def test_unified_context_is_one_page_and_cannot_collect_or_persist() -> None:
    report = V46IntelligenceFoundationService().unified_creative_context("pilot", _context())

    assert report.planning_only is True
    assert report.context.page_count == 1
    assert report.context.context_collected is False
    assert report.context.context_persisted is False
    assert report.provenance.redaction_required is True
    assert report.summary.implicit_collection_performed is False
    assert report.summary.automatic_action_taken is False


def test_cross_agent_memory_cannot_read_write_synchronize_or_grant_access() -> None:
    report = V46IntelligenceFoundationService().cross_agent_memory("pilot", _context())

    assert report.planning_only is True
    assert report.memory.page_count == 1
    assert report.memory.memory_read is False
    assert report.memory.memory_written is False
    assert report.memory.memory_synchronized is False
    assert report.consent.provenance_required is True
    assert report.consent.consent_required is True
    assert report.consent.access_granted is False
    assert report.summary.automatic_retrieval_performed is False


def test_creative_reasoning_is_human_reviewed_and_cannot_infer_or_delegate() -> None:
    report = V46IntelligenceFoundationService().creative_reasoning("pilot", _context())

    assert report.planning_only is True
    assert report.reasoning.page_count == 1
    assert report.reasoning.autonomous_inference_performed is False
    assert report.reasoning.content_generated is False
    assert report.recommendation.human_review_required is True
    assert report.recommendation.recommendation_accepted is False
    assert report.summary.agent_delegated is False
    assert report.summary.automatic_action_taken is False


def test_adaptive_workflow_preserves_state_machine_and_cannot_mutate_or_execute() -> None:
    report = V46IntelligenceFoundationService().adaptive_workflow("pilot", _context())

    assert report.planning_only is True
    assert report.proposal.page_count == 1
    assert report.proposal.state_machine_authoritative is True
    assert report.proposal.workflow_mutated is False
    assert report.proposal.workflow_executed is False
    assert report.safety.storyboard_required is True
    assert report.safety.quality_review_required is True
    assert report.safety.human_approval_required is True
    assert report.safety.stage_skipped is False
    assert report.summary.schedule_created is False
    assert report.summary.recovery_attempted is False


def test_intelligence_hub_is_transport_neutral_and_cannot_publish_or_operate() -> None:
    report = V46IntelligenceFoundationService().intelligence_hub("pilot", _context())

    assert report.planning_only is True
    assert report.hub.page_count == 1
    assert report.hub.presentation_dependency is False
    assert report.hub.hub_persisted is False
    assert report.hub.telemetry_collected is False
    assert report.summary.context_composed is True
    assert report.summary.human_review_required is True
    assert report.summary.published is False
    assert report.summary.operational_action_taken is False


def test_unified_context_rejects_more_than_one_page_scope() -> None:
    with pytest.raises(ValidationError):
        V46UnifiedCreativeContextDTO(
            context_id="context",
            project_id="project",
            page_reference="page",
            page_count=2,
            workflow_state=PageState.DRAFT.value,
        )


def test_v4_6_foundation_keeps_delivery_repository_and_runtime_boundaries_out_of_module() -> None:
    source = (ROOT / "src/manga_director/production/v4_6_intelligence_foundation.py").read_text(
        encoding="utf-8"
    )

    assert "manga_director.api" not in source
    assert "manga_director.cli" not in source
    assert "manga_director.mcp" not in source
    assert "manga_director.repositories" not in source
    assert "save(" not in source
    assert ".execute(" not in source
    assert "workflow_engine" not in source


def test_v4_6_foundation_docs_report_quality_gates_and_debt_are_available() -> None:
    assets = (
        "docs/UNIFIED_CONTEXT_FOUNDATION.md",
        "docs/CROSS_AGENT_MEMORY.md",
        "docs/CREATIVE_REASONING_FOUNDATION.md",
        "docs/INTELLIGENCE_HUB_FOUNDATION.md",
        "docs/ADAPTIVE_WORKFLOW_FOUNDATION.md",
        "docs/V4_6_ITERATION_1_CREATIVE_INTELLIGENCE_FOUNDATION_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    for gate in (
        "Unified Context Foundation Validation",
        "Cross-Agent Memory Foundation Validation",
        "Creative Reasoning Foundation Validation",
        "Intelligence Hub Foundation Validation",
        "Adaptive Workflow Foundation Validation",
    ):
        assert gate in gates
    for category in (
        "Unified Creative Context Foundation",
        "Cross-Agent Memory Foundation",
        "Creative Reasoning Foundation",
        "Intelligence Hub Foundation",
        "Adaptive Workflow Foundation",
    ):
        assert category in debt
