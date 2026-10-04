"""Contracts for the additive v3.4 governance DTOs."""

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
from manga_director.production import V34FoundationService, V34GovernanceService, V34InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _service() -> tuple[V34GovernanceService, InMemoryRepository]:
    repository = InMemoryRepository()
    repository.save(
        Project(
            id="pilot",
            title="Pilot",
            chapters=[Chapter(id="one", title="One", page_numbers=[1])],
            pages=[Page(page_number=1, storyboard={"panels": []})],
            metadata={"reference": {"secret": "not exposed"}},
        )
    )
    foundation = V34FoundationService(repository)
    insights = V34InsightsService(foundation, repository)
    return V34GovernanceService(foundation, insights, repository), repository


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.QUALITY_CHECKED,
        artifacts={"storyboard": {"panels": []}, "prompt": {"text": "not exposed"}},
        metadata={"workflow_history": [{"step": "quality", "to": "QualityChecked"}]},
    )


def test_knowledge_governance_is_redacted_read_only_and_cannot_apply_retention() -> None:
    service, repository = _service()

    report = service.knowledge_governance("pilot", _context())

    assert report.analysis_only is True
    assert all(policy.enforcement_applied is False for policy in report.policies)
    assert report.audit.audit_persisted is False
    assert report.retention.retention_evaluated is False
    assert report.retention.retention_applied is False
    assert report.summary.repository_mutated is False
    assert "not exposed" not in report.model_dump_json()
    assert repository.load("pilot").metadata["reference"] == {"secret": "not exposed"}


def test_production_governance_cannot_enforce_or_change_pipeline() -> None:
    service, repository = _service()
    context = _context()

    report = service.production_governance("pilot", context)

    assert report.analysis_only is True
    assert all(policy.enforcement_applied is False for policy in report.policies)
    assert report.operations.pipeline_changed is False
    assert report.operations.operation_started is False
    assert report.compliance.policy_enforced is False
    assert report.compliance.approval_authorized is False
    assert report.summary.workflow_modified is False
    assert context.state is PageState.QUALITY_CHECKED
    assert repository.load("pilot").title == "Pilot"


def test_organization_governance_cannot_score_or_change_people() -> None:
    service, _ = _service()

    report = service.organization_governance("pilot", _context())

    assert report.analysis_only is True
    assert all(policy.enforcement_applied is False for policy in report.policies)
    assert all(item.personnel_action_taken is False for item in report.compliance)
    assert report.audit.audit_persisted is False
    assert report.summary.organization_changed is False
    assert report.summary.automatic_action_taken is False


def test_release_governance_cannot_authorize_or_publish() -> None:
    service, _ = _service()

    report = service.release_governance("pilot", _context())

    assert report.analysis_only is True
    assert all(policy.enforcement_applied is False for policy in report.policies)
    assert all(item.remediation_applied is False for item in report.compliance)
    assert report.audit.audit_persisted is False
    assert report.summary.release_authorized is False
    assert report.summary.automatic_action_taken is False


def test_v3_4_governance_is_available_via_fastapi_mcp_and_cli_dto_boundaries() -> None:
    service, _ = _service()
    context = _context()
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
        knowledge_governance_v34=lambda: service.knowledge_governance_dashboard("pilot", context),
        production_governance_v34=lambda: service.production_governance_dashboard("pilot", context),
        organization_governance_v34=lambda: service.organization_governance_dashboard(
            "pilot", context
        ),
        release_governance_v34=lambda: service.release_governance_dashboard("pilot", context),
    )
    registry = default_tool_registry(
        cast(MangaApplicationService, None),
        knowledge_governance_v34_provider=lambda: service.knowledge_governance_dashboard(
            "pilot", context
        ),
        production_governance_v34_provider=lambda: service.production_governance_dashboard(
            "pilot", context
        ),
        organization_governance_v34_provider=lambda: service.organization_governance_dashboard(
            "pilot", context
        ),
        release_governance_v34_provider=lambda: service.release_governance_dashboard(
            "pilot", context
        ),
    )

    assert application.knowledge_governance_v34_preview()["automatic_action_taken"] is False
    assert application.production_governance_v34_preview()["report"]["analysis_only"] is True
    assert application.organization_governance_v34_preview()["automatic_action_taken"] is False
    assert application.release_governance_v34_preview()["automatic_action_taken"] is False
    routes = {route.path for route in create_observability_app(application).routes}
    assert {
        "/v3.4/knowledge-governance",
        "/v3.4/production-governance",
        "/v3.4/organization-governance",
        "/v3.4/release-governance",
    } <= routes
    assert {
        "knowledge_governance_v34",
        "production_governance_v34",
        "organization_governance_v34",
        "release_governance_v34",
    } <= {tool["name"] for tool in registry.list()}
    assert (
        CliRunner().invoke(app, ["director", "knowledge-governance-v34", "--help"]).exit_code == 0
    )


def test_v3_4_governance_docs_examples_and_benchmarks_are_available() -> None:
    assets = (
        "docs/KNOWLEDGE_GOVERNANCE.md",
        "docs/PRODUCTION_GOVERNANCE_V3_4.md",
        "docs/ORGANIZATION_GOVERNANCE.md",
        "docs/RELEASE_GOVERNANCE.md",
        "docs/V3_4_ITERATION_3_GOVERNANCE_REPORT.md",
        "examples/knowledge_governance/run.py",
        "examples/production_governance/v3_4_governance.py",
        "examples/organization_governance/run.py",
        "examples/release_governance/run.py",
        "examples/governance_dashboard/v3_4_governance.py",
        "benchmarks/knowledge_governance.py",
        "benchmarks/production_governance_v34.py",
        "benchmarks/organization_governance.py",
        "benchmarks/release_governance.py",
        "benchmarks/governance_dashboard_v34.py",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
