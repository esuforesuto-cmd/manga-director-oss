"""Contracts for non-executing v4.6 Creative Intelligence OS reports."""

from __future__ import annotations

from pathlib import Path

from manga_director.domain.state_machine import PageState
from manga_director.production import V46IntelligenceService
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}},
        metadata={"provenance": "human"},
    )


def test_context_intelligence_cannot_collect_persist_or_act() -> None:
    report = V46IntelligenceService().context_intelligence("pilot", _context())

    assert report.planning_only is True
    assert report.insight.page_count == 1
    assert report.insight.provenance_status == "not_assessed"
    assert report.insight.freshness_status == "not_assessed"
    assert report.insight.context_collected is False
    assert report.recommendation.context_persisted is False
    assert report.recommendation.automatic_action_taken is False


def test_reasoning_engine_cannot_update_model_decide_or_accept() -> None:
    report = V46IntelligenceService().reasoning_engine("pilot", _context())

    assert report.planning_only is True
    assert report.analysis.page_count == 1
    assert report.analysis.analysis_status == "not_assessed"
    assert report.analysis.model_updated is False
    assert report.analysis.autonomous_decision_made is False
    assert report.explanation.human_review_required is True
    assert report.explanation.recommendation_accepted is False


def test_adaptive_workflow_intelligence_cannot_mutate_execute_or_schedule() -> None:
    report = V46IntelligenceService().adaptive_workflow_intelligence("pilot", _context())

    assert report.planning_only is True
    assert report.insight.page_count == 1
    assert report.insight.state_machine_authoritative is True
    assert report.insight.dependency_analysis_completed is False
    assert report.insight.workflow_mutated is False
    assert report.insight.workflow_executed is False
    assert report.recommendation.stage_change_approved is False
    assert report.recommendation.schedule_created is False
    assert report.recommendation.automatic_action_taken is False


def test_knowledge_sharing_cannot_share_message_synchronize_or_grant_access() -> None:
    report = V46IntelligenceService().knowledge_sharing("pilot", _context())

    assert report.planning_only is True
    assert report.sharing.page_count == 1
    assert report.sharing.provenance_required is True
    assert report.sharing.consent_required is True
    assert report.sharing.redaction_required is True
    assert report.sharing.knowledge_shared is False
    assert report.sharing.agent_messaged is False
    assert report.sharing.memory_synchronized is False
    assert report.recommendation.access_granted is False
    assert report.recommendation.automatic_action_taken is False


def test_intelligence_dashboard_composes_reports_without_persistence_or_publication() -> None:
    report = V46IntelligenceService().intelligence_dashboard("pilot", _context())

    assert report.planning_only is True
    assert report.dashboard.page_count == 1
    assert report.dashboard.page_reference == "pilot-1"
    assert report.dashboard.context.insight.context_collected is False
    assert report.dashboard.reasoning.analysis.autonomous_decision_made is False
    assert report.dashboard.workflow.insight.workflow_executed is False
    assert report.dashboard.knowledge_sharing.sharing.knowledge_shared is False
    assert report.dashboard.presentation_dependency is False
    assert report.dashboard.dashboard_persisted is False
    assert report.dashboard.dashboard_published is False


def test_v4_6_intelligence_keeps_delivery_repository_and_runtime_boundaries_out_of_module() -> None:
    source = (ROOT / "src/manga_director/production/v4_6_intelligence.py").read_text(
        encoding="utf-8"
    )

    assert "manga_director.api" not in source
    assert "manga_director.cli" not in source
    assert "manga_director.mcp" not in source
    assert "manga_director.repositories" not in source
    assert "save(" not in source
    assert ".execute(" not in source
    assert "workflow_engine" not in source


def test_v4_6_intelligence_docs_report_quality_gates_and_debt_are_available() -> None:
    assets = (
        "docs/CONTEXT_INTELLIGENCE.md",
        "docs/REASONING_ENGINE.md",
        "docs/ADAPTIVE_WORKFLOW_INTELLIGENCE.md",
        "docs/KNOWLEDGE_SHARING.md",
        "docs/INTELLIGENCE_DASHBOARD.md",
        "docs/V4_6_ITERATION_2_CREATIVE_INTELLIGENCE_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")
    debt = (ROOT / "docs/TECH_DEBT.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    for gate in (
        "Context Intelligence Validation",
        "Reasoning Engine Validation",
        "Adaptive Workflow Intelligence Validation",
        "Cross-Agent Knowledge Sharing Validation",
        "Intelligence Dashboard Validation",
    ):
        assert gate in gates
    for category in (
        "Context Intelligence",
        "Reasoning Engine",
        "Adaptive Workflow Intelligence",
        "Cross-Agent Knowledge Sharing",
        "Intelligence Dashboard",
    ):
        assert category in debt
