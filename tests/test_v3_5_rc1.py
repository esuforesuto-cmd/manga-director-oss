"""RC1 contracts for the additive v3.5 delivery and review boundary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from typer.testing import CliRunner

import manga_director
from manga_director.api import ObservabilityApplication
from manga_director.api.observability import create_observability_app
from manga_director.cli.app import app
from manga_director.domain.project import Chapter, Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.mcp import McpServer
from manga_director.mcp.application import MangaApplicationService
from manga_director.mcp.registry import default_tool_registry
from manga_director.production import V35FoundationService, V35GovernanceService, V35InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}, "prompt": {"text": "redacted"}},
        metadata={"workflow_history": [{"step": "prompt", "to": "PromptBuilt"}]},
    )


def _services() -> tuple[
    V35FoundationService, V35InsightsService, V35GovernanceService, InMemoryRepository
]:
    repository = InMemoryRepository()
    repository.save(
        Project(
            id="pilot",
            title="Pilot",
            chapters=[Chapter(id="one", title="One", page_numbers=[1])],
            pages=[Page(page_number=1, storyboard={"panels": []})],
            metadata={"secret": "redacted"},
        )
    )
    foundation = V35FoundationService(repository)
    insights = V35InsightsService(foundation, repository)
    return foundation, insights, V35GovernanceService(foundation, insights, repository), repository


def test_v3_5_rc1_version_is_single_source_for_package_openapi_mcp_and_frontend() -> None:
    frontend = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    lockfile = json.loads((ROOT / "web/package-lock.json").read_text(encoding="utf-8"))
    sbom = json.loads((ROOT / "docs/SBOM.spdx.json").read_text(encoding="utf-8"))
    api = create_observability_app(
        ObservabilityApplication(
            health=lambda: None,  # type: ignore[arg-type]
            diagnostics=lambda: None,  # type: ignore[arg-type]
            repository_check=lambda: None,  # type: ignore[arg-type]
        )
    )
    server = McpServer(tool_registry=None, resources=None, prompts=None)  # type: ignore[arg-type]
    initialized = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})

    assert manga_director.__version__ == "6.0.0"
    assert api.version == manga_director.__version__
    assert initialized is not None
    assert initialized["result"]["serverInfo"]["version"] == manga_director.__version__
    assert frontend["version"] == manga_director.__version__.replace("rc", "-rc.")
    assert lockfile["version"] == frontend["version"]
    assert lockfile["packages"][""]["version"] == frontend["version"]
    assert sbom["packages"][0]["versionInfo"] == manga_director.__version__


def test_v3_5_rc1_integration_is_read_only_and_preserves_save_reload_flow() -> None:
    foundation, insights, governance, repository = _services()
    context = _context()

    graph = foundation.knowledge_graph("pilot", context)
    creative = insights.creative_analytics("pilot", context)
    production = insights.production_analytics("pilot", context)
    platform = insights.platform_intelligence("pilot", context)
    knowledge_governance = governance.knowledge_governance("pilot", context)
    creative_governance = governance.creative_governance("pilot", context)
    production_governance = governance.production_governance("pilot", context)
    platform_governance = governance.platform_governance("pilot", context)

    assert graph.analysis_only is True
    assert creative.analysis_only is True
    assert production.analysis_only is True
    assert platform.analysis_only is True
    assert knowledge_governance.summary.repository_mutated is False
    assert creative_governance.automatic_action_taken is False
    assert production_governance.summary.automatic_action_taken is False
    assert platform_governance.summary.automatic_action_taken is False
    assert repository.load("pilot").pages[0].storyboard == {"panels": []}


def test_v3_5_rc1_architecture_keeps_v3_5_services_out_of_delivery_layers() -> None:
    modules = (
        ROOT / "src/manga_director/production/v3_5_foundation.py",
        ROOT / "src/manga_director/production/v3_5_insights.py",
        ROOT / "src/manga_director/production/v3_5_governance.py",
    )

    for module in modules:
        source = module.read_text(encoding="utf-8")
        assert "manga_director.api" not in source
        assert "manga_director.cli" not in source
        assert "manga_director.mcp" not in source
        assert "save(" not in source
        assert "workflow_engine" not in source


def test_v3_5_rc1_delivery_surfaces_expose_only_additive_dashboard_dtos() -> None:
    foundation, insights, governance, _ = _services()
    context = _context()
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
        knowledge_graph_v35=lambda: foundation.knowledge_graph_dashboard("pilot", context),
        creative_analytics_v35=lambda: insights.creative_analytics_dashboard("pilot", context),
        production_analytics_v35=lambda: insights.production_analytics_dashboard("pilot", context),
        executive_analytics_v35=lambda: insights.executive_analytics_dashboard("pilot", context),
        knowledge_governance_v35=lambda: governance.knowledge_governance_dashboard(
            "pilot", context
        ),
        creative_governance_v35=lambda: governance.creative_governance_dashboard("pilot", context),
        production_governance_v35=lambda: governance.production_governance_dashboard(
            "pilot", context
        ),
        platform_governance_v35=lambda: governance.platform_governance_dashboard("pilot", context),
    )
    registry = default_tool_registry(
        cast(MangaApplicationService, None),
        knowledge_graph_v35_provider=lambda: foundation.knowledge_graph_dashboard("pilot", context),
        creative_analytics_v35_provider=lambda: insights.creative_analytics_dashboard(
            "pilot", context
        ),
        production_analytics_v35_provider=lambda: insights.production_analytics_dashboard(
            "pilot", context
        ),
        executive_analytics_v35_provider=lambda: insights.executive_analytics_dashboard(
            "pilot", context
        ),
        knowledge_governance_v35_provider=lambda: governance.knowledge_governance_dashboard(
            "pilot", context
        ),
        creative_governance_v35_provider=lambda: governance.creative_governance_dashboard(
            "pilot", context
        ),
        production_governance_v35_provider=lambda: governance.production_governance_dashboard(
            "pilot", context
        ),
        platform_governance_v35_provider=lambda: governance.platform_governance_dashboard(
            "pilot", context
        ),
    )

    assert application.knowledge_graph_v35_preview()["automatic_action_taken"] is False
    assert application.creative_analytics_v35_preview()["automatic_action_taken"] is False
    assert application.production_analytics_v35_preview()["automatic_action_taken"] is False
    assert application.executive_analytics_v35_preview()["automatic_action_taken"] is False
    assert application.knowledge_governance_v35_preview()["automatic_action_taken"] is False
    routes = {route.path for route in create_observability_app(application).routes}
    assert {
        "/v3.4/knowledge-platform",
        "/v3.4/production-governance",
        "/v3.5/knowledge-graph",
        "/v3.5/creative-analytics",
        "/v3.5/production-analytics",
        "/v3.5/executive-analytics",
        "/v3.5/knowledge-governance",
        "/v3.5/creative-governance",
        "/v3.5/production-governance",
        "/v3.5/platform-governance",
    } <= routes
    assert {
        "knowledge_governance_v34",
        "production_governance_v34",
        "knowledge_graph_v35",
        "creative_analytics_v35",
        "production_analytics_v35",
        "executive_analytics_v35",
        "knowledge_governance_v35",
        "creative_governance_v35",
        "production_governance_v35",
        "platform_governance_v35",
    } <= {tool["name"] for tool in registry.list()}
    assert CliRunner().invoke(app, ["director", "knowledge-graph-v35", "--help"]).exit_code == 0


def test_v3_5_rc1_release_assets_and_quality_gates_are_available() -> None:
    assets = (
        "RELEASE_V3_5_RC1.md",
        "docs/ARCHITECTURE_SUMMARY_V3_5_RC1.md",
        "docs/COMPATIBILITY_V3_5_RC1.md",
        "docs/WORKFLOW_REGRESSION_V3_5_RC1.md",
        "docs/BENCHMARK_V3_5_RC1.md",
        "docs/SECURITY_AUDIT_V3_5_RC1.md",
        "docs/RELEASE_CHECKLIST_V3_5_RC1.md",
        "docs/V3_5_RC1_READINESS_REPORT.md",
    )
    gates = (ROOT / "docs/V3_5_QUALITY_GATES.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    assert "RC Readiness Validation" in gates
    assert "Release Compatibility Validation" in gates
    assert "Performance Regression Validation" in gates
    assert "Documentation Validation" in gates
