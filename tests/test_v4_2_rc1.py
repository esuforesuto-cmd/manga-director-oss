"""RC1 contracts for additive v4.2 Autonomous Creative System modules."""

from __future__ import annotations

import json
import re
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
    V42AutonomousFoundationService,
    V42AutonomousOperationsService,
    V42AutonomousWorkflowService,
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


def _repository() -> InMemoryRepository:
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
    return repository


def test_v4_2_rc1_version_is_canonical_for_package_openapi_mcp_frontend_and_sbom() -> None:
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


def test_v4_2_rc1_e2e_projection_preserves_save_reload_review_reporting_and_boundaries() -> None:
    context = _context()
    foundation = V42AutonomousFoundationService()
    workflow = V42AutonomousWorkflowService()
    operations = V42AutonomousOperationsService()
    repository = _repository()

    goal = workflow.goal_management("pilot", context, "Prepare one page for human review")
    planning = workflow.adaptive_planning("pilot", context, "Prepare one page for human review")
    execution = foundation.execution("pilot", context, "Prepare one page for human review")
    checkpoint = foundation.checkpoint("pilot", context)
    supervisor = foundation.supervisor("pilot", context)
    supervision = operations.human_supervision("pilot", context)
    pipeline = workflow.pipeline_automation("pilot", context)
    operations_report = operations.operations("pilot", context)
    reloaded = repository.load("pilot")

    assert goal.manager.goal.page_count == 1
    assert planning.revision.revision_applied is False
    assert execution.session.session_started is False
    assert checkpoint.resume_result.resumed is False
    assert supervisor.escalation.escalation_sent is False
    assert supervision.approval_checkpoint.approval_granted is False
    assert pipeline.stage_result.result_status == "not_run"
    assert operations_report.governance.safety_boundary.state_machine_authoritative is True
    assert operations_report.reliability.retry_policy.max_automatic_attempts == 0
    assert reloaded.pages[0].storyboard == {"panels": []}


def test_v4_2_rc1_architecture_keeps_autonomous_modules_out_of_delivery_and_write_layers() -> None:
    modules = (
        ROOT / "src/manga_director/production/v4_2_autonomous_foundation.py",
        ROOT / "src/manga_director/production/v4_2_autonomous_workflow.py",
        ROOT / "src/manga_director/production/v4_2_autonomous_operations.py",
    )

    for module in modules:
        source = module.read_text(encoding="utf-8")
        assert "manga_director.api" not in source
        assert "manga_director.cli" not in source
        assert "manga_director.mcp" not in source
        assert "manga_director.repositories" not in source
        assert "save(" not in source
        assert ".execute(" not in source
        assert "workflow_engine" not in source


def test_v4_2_rc1_existing_cli_fastapi_mcp_and_web_ui_contracts_remain_available() -> None:
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


def test_v4_2_rc1_release_assets_and_quality_gates_are_available() -> None:
    assets = (
        "RELEASE_V4_2_RC1.md",
        "docs/ARCHITECTURE_SUMMARY_V4_2_RC1.md",
        "docs/COMPATIBILITY_V4_2_RC1.md",
        "docs/WORKFLOW_REGRESSION_V4_2_RC1.md",
        "docs/BENCHMARK_V4_2_RC1.md",
        "docs/SECURITY_AUDIT_V4_2_RC1.md",
        "docs/RELEASE_CHECKLIST_V4_2_RC1.md",
        "docs/V4_2_RC1_READINESS_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    assert "Autonomous Readiness Validation" in gates
    assert "Release Compatibility Validation" in gates
    assert "Performance Regression Validation" in gates
    assert "Documentation Validation" in gates


def test_v4_2_rc1_updated_documentation_links_are_resolvable() -> None:
    documents = (
        ROOT / "README.md",
        ROOT / "RELEASE_V4_2_RC1.md",
        ROOT / "docs/ARCHITECTURE_SUMMARY_V4_2_RC1.md",
        ROOT / "docs/COMPATIBILITY_V4_2_RC1.md",
        ROOT / "docs/WORKFLOW_REGRESSION_V4_2_RC1.md",
        ROOT / "docs/BENCHMARK_V4_2_RC1.md",
        ROOT / "docs/SECURITY_AUDIT_V4_2_RC1.md",
        ROOT / "docs/RELEASE_CHECKLIST_V4_2_RC1.md",
        ROOT / "docs/V4_2_RC1_READINESS_REPORT.md",
    )

    for document in documents:
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", document.read_text(encoding="utf-8")):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            assert (document.parent / link).exists(), f"{document}: broken link to {link}"
