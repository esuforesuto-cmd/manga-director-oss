"""Contracts for v3.2 Iteration 3 reliability and readiness diagnostics."""

from __future__ import annotations

from typing import cast

from typer.testing import CliRunner

from manga_director.api import ObservabilityApplication
from manga_director.api.observability import create_observability_app
from manga_director.cli.app import app
from manga_director.domain.project import Chapter, Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.mcp.application import MangaApplicationService
from manga_director.mcp.registry import default_tool_registry
from manga_director.production import V32AssuranceService, V32FoundationService, V32InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def _service() -> tuple[V32AssuranceService, InMemoryRepository]:
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
    foundation = V32FoundationService(repository)
    insights = V32InsightsService(foundation, repository)
    return V32AssuranceService(foundation, insights, repository), repository


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1"},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}, "prompt": {"text": "not exposed"}},
        metadata={"workflow_history": [{"step": "prompt", "to": "PromptBuilt"}]},
    )


def test_creative_reliability_is_diagnostic_and_preserves_one_page_workflow() -> None:
    service, repository = _service()
    context = _context()

    report = service.creative_reliability("pilot", context)

    assert report.validation.workflow_executed is False
    assert report.validation.approval_granted is False
    assert report.integrity.one_page_scope is True
    assert report.workspace.workspace_persisted is False
    assert report.readiness.auto_approved is False
    assert context.state is PageState.PROMPT_BUILT
    assert repository.load("pilot").title == "Pilot"


def test_asset_governance_is_redacted_and_never_repairs_or_scores_assets() -> None:
    service, repository = _service()

    report = service.asset_governance("pilot", _context())

    assert report.integrity.metadata_values_redacted is True
    assert report.integrity.repository_repaired is False
    assert report.lifecycle.lifecycle_managed is False
    assert report.quality.score == "not_computed"
    assert report.risk.remediation_applied is False
    assert repository.load("pilot").metadata["reference"]["secret"] == "not exposed"


def test_operational_intelligence_is_analysis_only_and_never_deploys_or_recovers() -> None:
    service, _ = _service()

    report = service.operational_intelligence(_context())

    assert report.operational.operations_changed is False
    assert report.workflow.workflow_recovered is False
    assert report.analytics.analytics_persisted is False
    assert report.trend.external_collection_started is False
    assert report.deployment.deployment_started is False
    assert report.summary.automation_started is False


def test_release_readiness_has_no_release_authorization_or_regression_remediation() -> None:
    service, _ = _service()

    report = service.release_readiness(_context())

    assert report.readiness.release_started is False
    assert report.compatibility.public_interface_changed is False
    assert report.regression.remediation_applied is False
    assert report.quality_gates.gate_enforced is False
    assert report.production.production_changed is False
    assert report.recommendation.release_authorized is False


def test_compatibility_validation_is_dto_only_for_fastapi_mcp_and_cli() -> None:
    service, _ = _service()
    context = _context()
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
        creative_reliability_v32=lambda: service.creative_reliability_dashboard("pilot", context),
        asset_governance_v32=lambda: service.asset_governance_dashboard("pilot", context),
        operational_intelligence_v32=lambda: service.operational_intelligence_dashboard(context),
        release_readiness_v32=lambda: service.release_readiness_dashboard(context),
        compatibility_validation_v32=lambda: (
            service.release_readiness_dashboard(context).report.compatibility
        ),
    )
    registry = default_tool_registry(
        cast(MangaApplicationService, None),
        creative_reliability_v32_provider=lambda: service.creative_reliability_dashboard(
            "pilot", context
        ),
        asset_governance_v32_provider=lambda: service.asset_governance_dashboard("pilot", context),
        operational_intelligence_v32_provider=lambda: service.operational_intelligence_dashboard(
            context
        ),
        release_readiness_v32_provider=lambda: service.release_readiness_dashboard(context),
        compatibility_validation_v32_provider=lambda: (
            service.release_readiness_dashboard(context).report.compatibility
        ),
    )

    assert application.creative_reliability_v32_preview()["automatic_action_taken"] is False
    assert application.asset_governance_v32_preview()["report"]["analysis_only"] is True
    assert application.operational_intelligence_v32_preview()["automatic_action_taken"] is False
    assert application.release_readiness_v32_preview()["automatic_action_taken"] is False
    assert application.compatibility_validation_v32_preview()["public_interface_changed"] is False
    routes = {route.path for route in create_observability_app(application).routes}
    assert {
        "/v3.2/creative-reliability",
        "/v3.2/asset-governance",
        "/v3.2/operational-intelligence",
        "/v3.2/release-readiness",
        "/v3.2/compatibility-validation",
    } <= routes
    assert registry.invoke("creative_reliability_v32", {}).data["automatic_action_taken"] is False
    assert registry.invoke("asset_governance_v32", {}).data["report"]["analysis_only"] is True
    assert (
        registry.invoke("operational_intelligence_v32", {}).data["automatic_action_taken"] is False
    )
    assert registry.invoke("release_readiness_v32", {}).data["automatic_action_taken"] is False
    assert (
        registry.invoke("compatibility_validation_v32", {}).data["public_interface_changed"]
        is False
    )
    command_help = CliRunner().invoke(app, ["director", "--help"])
    assert command_help.exit_code == 0
    assert "creative-reliability" in command_help.output
    assert "asset-governance" in command_help.output
    assert "operational-intelligence-v32" in command_help.output
    assert "release-readiness-v32" in command_help.output
    assert "compatibility-validation-v32" in command_help.output
