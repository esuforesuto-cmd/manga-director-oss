"""Contracts for the additive v3.3 Iteration 3 governance DTOs."""

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
from manga_director.production import V33FoundationService, V33GovernanceService, V33InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _service() -> tuple[V33GovernanceService, InMemoryRepository]:
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
    foundation = V33FoundationService(repository)
    insights = V33InsightsService(foundation, repository)
    return V33GovernanceService(foundation, insights, repository), repository


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}, "prompt": {"text": "not exposed"}},
        metadata={"workflow_history": [{"step": "prompt", "to": "PromptBuilt"}]},
    )


def test_production_governance_cannot_enforce_or_change_a_pipeline() -> None:
    service, repository = _service()
    context = _context()

    report = service.production_governance("pilot", context)

    assert report.analysis_only is True
    assert all(policy.enforcement_applied is False for policy in report.policies)
    assert report.pipeline.pipeline_changed is False
    assert report.pipeline.execution_started is False
    assert report.compliance.policy_enforced is False
    assert report.compliance.approval_authorized is False
    assert context.state is PageState.PROMPT_BUILT
    assert repository.load("pilot").title == "Pilot"


def test_quality_governance_cannot_remediate_or_approve() -> None:
    service, _ = _service()

    report = service.quality_governance(_context())

    assert report.analysis_only is True
    assert all(policy.enforcement_applied is False for policy in report.policies)
    assert all(item.correction_applied is False for item in report.compliance.compliance)
    assert report.compliance.approval_authorized is False
    assert report.compliance.remediation_applied is False


def test_asset_governance_is_redacted_and_cannot_apply_retention() -> None:
    service, repository = _service()

    report = service.asset_governance("pilot", _context())

    assert report.analysis_only is True
    assert report.governance.values_redacted is True
    assert report.retention.retention_evaluated is False
    assert report.retention.retention_applied is False
    assert report.summary.repository_mutated is False
    assert "not exposed" not in report.model_dump_json()
    assert repository.load("pilot").metadata["reference"] == {"secret": "not exposed"}


def test_project_governance_cannot_schedule_allocate_or_commit_delivery() -> None:
    service, _ = _service()

    report = service.project_governance("pilot", _context())

    assert report.analysis_only is True
    assert report.governance.operation_started is False
    assert report.risk.risk_accepted is False
    assert report.risk.mitigation_applied is False
    assert report.summary.delivery_committed is False
    assert report.summary.automatic_action_taken is False


def test_v3_3_governance_is_available_via_fastapi_mcp_and_cli_dto_boundaries() -> None:
    service, _ = _service()
    context = _context()
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
        production_governance_v33=lambda: service.production_governance_dashboard("pilot", context),
        quality_governance_v33=lambda: service.quality_governance_dashboard(context),
        asset_governance_v33=lambda: service.asset_governance_dashboard("pilot", context),
        project_governance_v33=lambda: service.project_governance_dashboard("pilot", context),
    )
    registry = default_tool_registry(
        cast(MangaApplicationService, None),
        production_governance_v33_provider=lambda: service.production_governance_dashboard(
            "pilot", context
        ),
        quality_governance_v33_provider=lambda: service.quality_governance_dashboard(context),
        asset_governance_v33_provider=lambda: service.asset_governance_dashboard("pilot", context),
        project_governance_v33_provider=lambda: service.project_governance_dashboard("pilot", context),
    )

    assert application.production_governance_v33_preview()["automatic_action_taken"] is False
    assert application.quality_governance_v33_preview()["report"]["analysis_only"] is True
    assert application.asset_governance_v33_preview()["report"]["summary"]["repository_mutated"] is False
    assert application.project_governance_v33_preview()["automatic_action_taken"] is False
    routes = {route.path for route in create_observability_app(application).routes}
    assert {
        "/v3.3/production-governance",
        "/v3.3/quality-governance",
        "/v3.3/asset-governance",
        "/v3.3/project-governance",
    } <= routes
    assert {
        "production_governance_v33",
        "quality_governance_v33",
        "asset_governance_v33",
        "project_governance_v33",
    } <= {tool["name"] for tool in registry.list()}
    assert CliRunner().invoke(app, ["director", "production-governance-v33", "--help"]).exit_code == 0


def test_v3_3_governance_docs_examples_and_benchmarks_are_available() -> None:
    assets = (
        "docs/PRODUCTION_GOVERNANCE.md",
        "docs/QUALITY_GOVERNANCE.md",
        "docs/ASSET_GOVERNANCE.md",
        "docs/PROJECT_GOVERNANCE.md",
        "docs/V3_3_ITERATION_3_GOVERNANCE_REPORT.md",
        "examples/production_governance/run.py",
        "examples/quality_governance/run.py",
        "examples/asset_governance/v3_3_governance.py",
        "examples/project_governance/run.py",
        "examples/governance_dashboard/run.py",
        "benchmarks/production_governance.py",
        "benchmarks/quality_governance.py",
        "benchmarks/asset_governance_v33.py",
        "benchmarks/project_governance.py",
        "benchmarks/governance_dashboard.py",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
