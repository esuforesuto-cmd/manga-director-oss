"""Contracts for v3.5 policy, compliance, and audit evidence."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from typer.testing import CliRunner

from manga_director.api import ObservabilityApplication
from manga_director.api.observability import create_observability_app
from manga_director.cli.app import app
from manga_director.domain.project import Chapter, Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.mcp.application import MangaApplicationService
from manga_director.mcp.registry import default_tool_registry
from manga_director.production import V35FoundationService, V35GovernanceService, V35InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _service() -> tuple[V35GovernanceService, InMemoryRepository]:
    repository = InMemoryRepository()
    repository.save(
        Project(
            id="pilot",
            title="Pilot",
            chapters=[Chapter(id="one", title="One", page_numbers=[1])],
            pages=[Page(page_number=1, storyboard={"panels": []})],
            metadata={"reference": {"secret": "not exposed"}, "world": "not exposed"},
        )
    )
    foundation = V35FoundationService(repository)
    return V35GovernanceService(
        foundation, V35InsightsService(foundation, repository), repository
    ), repository


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}, "prompt": {"text": "not exposed"}},
        metadata={"workflow_history": [{"step": "prompt", "to": "PromptBuilt"}]},
    )


def test_knowledge_governance_cannot_persist_or_enforce_policy() -> None:
    service, repository = _service()

    report = service.knowledge_governance("pilot", _context())

    assert report.analysis_only is True
    assert all(policy.enforcement_applied is False for policy in report.policies)
    assert all(item.compliance_verified is False for item in report.compliance)
    assert all(item.remediation_applied is False for item in report.compliance)
    assert report.audit.audit_persisted is False
    assert report.lifecycle.lifecycle_applied is False
    assert report.summary.repository_mutated is False
    assert repository.load("pilot").metadata["world"] == "not exposed"


def test_creative_governance_cannot_change_creative_work_or_approve_page() -> None:
    service, _ = _service()

    dashboard = service.creative_governance("pilot", _context())

    assert all(policy.enforcement_applied is False for policy in dashboard.policies)
    assert dashboard.quality.quality_completed is False
    assert dashboard.quality.approval_authorized is False
    assert dashboard.compliance.compliance_verified is False
    assert dashboard.compliance.creative_changed is False
    assert dashboard.audit.audit_persisted is False
    assert dashboard.automatic_action_taken is False


def test_production_governance_cannot_mutate_workflow_or_deploy() -> None:
    service, _ = _service()

    dashboard = service.production_governance("pilot", _context())

    assert dashboard.analysis_only is True
    assert all(policy.enforcement_applied is False for policy in dashboard.policies)
    assert dashboard.compliance.compliance_verified is False
    assert dashboard.compliance.workflow_modified is False
    assert dashboard.audit.audit_persisted is False
    assert dashboard.summary.optimization_applied is False
    assert dashboard.summary.deployment_started is False
    assert dashboard.summary.automatic_action_taken is False


def test_platform_governance_cannot_monitor_authorize_or_act() -> None:
    service, _ = _service()

    dashboard = service.platform_governance("pilot", _context())

    assert dashboard.analysis_only is True
    assert all(policy.enforcement_applied is False for policy in dashboard.policies)
    assert dashboard.audit.audit_persisted is False
    assert dashboard.compliance.compliance_verified is False
    assert dashboard.compliance.external_action_taken is False
    assert dashboard.summary.monitoring_started is False
    assert dashboard.summary.release_authorized is False
    assert dashboard.summary.automatic_action_taken is False


def test_v3_5_governance_dashboards_are_available_via_fastapi_mcp_and_cli() -> None:
    service, _ = _service()
    context = _context()
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
        knowledge_governance_v35=lambda: service.knowledge_governance_dashboard("pilot", context),
        creative_governance_v35=lambda: service.creative_governance_dashboard("pilot", context),
        production_governance_v35=lambda: service.production_governance_dashboard("pilot", context),
        platform_governance_v35=lambda: service.platform_governance_dashboard("pilot", context),
    )
    registry = default_tool_registry(
        cast(MangaApplicationService, None),
        knowledge_governance_v35_provider=lambda: service.knowledge_governance_dashboard(
            "pilot", context
        ),
        creative_governance_v35_provider=lambda: service.creative_governance_dashboard(
            "pilot", context
        ),
        production_governance_v35_provider=lambda: service.production_governance_dashboard(
            "pilot", context
        ),
        platform_governance_v35_provider=lambda: service.platform_governance_dashboard(
            "pilot", context
        ),
    )

    assert application.knowledge_governance_v35_preview()["automatic_action_taken"] is False
    assert (
        application.creative_governance_v35_preview()["report"]["automatic_action_taken"] is False
    )
    assert application.production_governance_v35_preview()["automatic_action_taken"] is False
    assert application.platform_governance_v35_preview()["automatic_action_taken"] is False
    routes = {route.path for route in create_observability_app(application).routes}
    assert {
        "/v3.5/knowledge-governance",
        "/v3.5/creative-governance",
        "/v3.5/production-governance",
        "/v3.5/platform-governance",
    } <= routes
    assert {
        "knowledge_governance_v35",
        "creative_governance_v35",
        "production_governance_v35",
        "platform_governance_v35",
    } <= {tool["name"] for tool in registry.list()}
    assert (
        CliRunner().invoke(app, ["director", "knowledge-governance-v35", "--help"]).exit_code == 0
    )


def test_v3_5_governance_docs_examples_and_benchmarks_are_available() -> None:
    assets = (
        "docs/KNOWLEDGE_GOVERNANCE.md",
        "docs/CREATIVE_GOVERNANCE.md",
        "docs/PRODUCTION_GOVERNANCE.md",
        "docs/PLATFORM_GOVERNANCE.md",
        "docs/V3_5_ITERATION_3_GOVERNANCE_REPORT.md",
        "examples/governance_dashboard/v3_5_governance.py",
        "examples/creative_governance/v3_5_governance.py",
        "examples/production_governance/v3_5_governance.py",
        "examples/platform_governance/run.py",
        "benchmarks/governance_dashboard_v35.py",
        "benchmarks/policy_validation_v35.py",
        "benchmarks/compliance_report_v35.py",
        "benchmarks/audit_generation_v35.py",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
