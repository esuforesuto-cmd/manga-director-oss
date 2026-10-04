"""RC1 contracts for additive v4.1 Creative Agent Platform modules."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import manga_director
from manga_director.api import ObservabilityApplication
from manga_director.api.observability import create_observability_app
from manga_director.cli.app import app
from manga_director.domain.project import Chapter, Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.mcp import McpServer
from manga_director.production import (
    AgentRegistryRepository,
    V4FoundationService,
    V41AgentDTO,
    V41AgentFoundationService,
    V41AgentProfileDTO,
    V41OrchestrationService,
    V41PlatformAssuranceService,
    V41RoleDTO,
)
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
    V4FoundationService,
    V41AgentFoundationService,
    V41OrchestrationService,
    V41PlatformAssuranceService,
    InMemoryRepository,
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
    agent = V41AgentDTO(
        agent_id="editor-1",
        profile=V41AgentProfileDTO(
            profile_id="editor-profile",
            display_name="Editor",
            role=V41RoleDTO(role_id="editor", name="Editor"),
        ),
    )
    registry = AgentRegistryRepository((agent,))
    return (
        V4FoundationService(repository),
        V41AgentFoundationService(registry),
        V41OrchestrationService(registry),
        V41PlatformAssuranceService(registry),
        repository,
    )


def test_v4_1_rc1_version_is_single_source_for_package_openapi_mcp_frontend_and_sbom() -> None:
    frontend = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    lockfile = json.loads((ROOT / "web/package-lock.json").read_text(encoding="utf-8"))
    sbom = json.loads((ROOT / "docs/SBOM.spdx.json").read_text(encoding="utf-8"))
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
    )
    initialized = McpServer(None, None, None).handle(  # type: ignore[arg-type]
        {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    )

    assert manga_director.__version__ == "6.0.0"
    assert create_observability_app(application).version == manga_director.__version__
    assert initialized is not None
    assert initialized["result"]["serverInfo"]["version"] == manga_director.__version__
    assert frontend["version"] == manga_director.__version__.replace("rc", "-rc.")
    assert lockfile["version"] == frontend["version"]
    assert lockfile["packages"][""]["version"] == frontend["version"]
    assert sbom["packages"][0]["versionInfo"] == manga_director.__version__


def test_v4_1_rc1_e2e_projection_preserves_review_save_reload_reporting_and_delivery_boundaries() -> (
    None
):
    workspace, agents, orchestration, assurance, repository = _services()
    context = _context()

    workspace_report = workspace.workspace("pilot", context)
    registry = agents.registry()
    plan = orchestration.planning("pilot", context)
    orchestration_report = orchestration.orchestration("pilot", context)
    collaboration = orchestration.collaboration_workflow("editor-1", "editor-1", "pilot", context)
    human_review = assurance.human_review("pilot", context)
    quality = workspace.quality("pilot", context)
    platform = assurance.platform_report("editor-1", "pilot", context)
    reloaded = repository.load("pilot")

    assert workspace_report.analysis_only is True
    assert len(registry.agents) == 1
    assert plan.summary.execution_enabled is False
    assert orchestration_report.summary.dispatched_task_count == 0
    assert collaboration.approval.approval_granted is False
    assert human_review.result.approved is False
    assert quality.editorial.review_completed is False
    assert quality.editorial.approval_granted is False
    assert platform.automatic_action_taken is False
    assert reloaded.pages[0].storyboard == {"panels": []}


def test_v4_1_rc1_architecture_keeps_agent_modules_out_of_delivery_and_write_layers() -> None:
    modules = (
        ROOT / "src/manga_director/production/v4_1_agent_foundation.py",
        ROOT / "src/manga_director/production/v4_1_orchestration.py",
        ROOT / "src/manga_director/production/v4_1_assurance.py",
    )

    for module in modules:
        source = module.read_text(encoding="utf-8")
        assert "manga_director.api" not in source
        assert "manga_director.cli" not in source
        assert "manga_director.mcp" not in source
        assert "save(" not in source
        assert ".execute(" not in source
        assert "workflow_engine" not in source


def test_v4_1_rc1_existing_cli_fastapi_mcp_and_web_ui_contracts_remain_available() -> None:
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
    )
    initialized = McpServer(None, None, None).handle(  # type: ignore[arg-type]
        {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    )
    package = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))

    assert CliRunner().invoke(app, ["--help"]).exit_code == 0
    assert {"/health", "/diagnostics", "/repository/check"} <= {
        route.path for route in create_observability_app(application).routes
    }
    assert initialized is not None
    assert initialized["result"]["serverInfo"]["version"] == manga_director.__version__
    assert package["name"] == "manga-director-web"


def test_v4_1_rc1_release_assets_and_quality_gates_are_available() -> None:
    assets = (
        "RELEASE_V4_1_RC1.md",
        "docs/ARCHITECTURE_SUMMARY_V4_1_RC1.md",
        "docs/COMPATIBILITY_V4_1_RC1.md",
        "docs/WORKFLOW_REGRESSION_V4_1_RC1.md",
        "docs/BENCHMARK_V4_1_RC1.md",
        "docs/SECURITY_AUDIT_V4_1_RC1.md",
        "docs/RELEASE_CHECKLIST_V4_1_RC1.md",
        "docs/V4_1_RC1_READINESS_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    assert "Multi-Agent Readiness Validation" in gates
    assert "Release Compatibility Validation" in gates
    assert "Performance Regression Validation" in gates
    assert "Documentation Validation" in gates
