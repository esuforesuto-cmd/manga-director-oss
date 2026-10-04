"""RC1 contracts for additive v4.3 Creative Production Platform modules."""

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
    V43ProductionFoundationService,
    V43ProductionIntelligenceService,
    V43ProductionOperationsService,
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


def test_v4_3_rc1_version_is_canonical_for_package_openapi_mcp_frontend_and_sbom() -> None:
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


def test_v4_3_rc1_e2e_projection_preserves_save_reload_review_reporting_and_boundaries() -> None:
    context = _context()
    foundation = V43ProductionFoundationService()
    intelligence = V43ProductionIntelligenceService(foundation)
    operations = V43ProductionOperationsService(intelligence)
    repository = _repository()

    pipeline = foundation.production_pipeline("pilot", context)
    asset = foundation.asset_management("pilot", context)
    workspace = foundation.project_workspace("pilot", context)
    deliverable = foundation.deliverables("pilot", context)
    publishing = intelligence.publishing_workflow("pilot", context)
    quality = operations.quality_assurance("pilot", context)
    governance = operations.production_governance("pilot", context)
    monitoring = operations.operations_monitoring("pilot", context)
    reliability = operations.platform_reliability("pilot", context)
    reloaded = repository.load("pilot")

    assert pipeline.project.page_count == 1
    assert pipeline.stage.stage_started is False
    assert asset.asset.asset_persisted is False
    assert workspace.task.dispatched is False
    assert quality.checklist.approval_granted is False
    assert deliverable.export_profile.export_performed is False
    assert publishing.distribution.external_delivery_performed is False
    assert governance.policy.state_machine_authoritative is True
    assert governance.summary.enforcement_action_taken is False
    assert monitoring.alert.alert_sent is False
    assert reliability.recovery_policy.automatic_recovery_enabled is False
    assert reloaded.pages[0].storyboard == {"panels": []}


def test_v4_3_rc1_architecture_keeps_production_modules_out_of_delivery_and_write_layers() -> None:
    modules = (
        ROOT / "src/manga_director/production/v4_3_production_foundation.py",
        ROOT / "src/manga_director/production/v4_3_production_intelligence.py",
        ROOT / "src/manga_director/production/v4_3_production_operations.py",
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


def test_v4_3_rc1_existing_cli_fastapi_mcp_and_web_ui_contracts_remain_available() -> None:
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


def test_v4_3_rc1_release_assets_and_quality_gates_are_available() -> None:
    assets = (
        "RELEASE_V4_3_RC1.md",
        "docs/ARCHITECTURE_SUMMARY_V4_3_RC1.md",
        "docs/COMPATIBILITY_V4_3_RC1.md",
        "docs/WORKFLOW_REGRESSION_V4_3_RC1.md",
        "docs/BENCHMARK_V4_3_RC1.md",
        "docs/SECURITY_AUDIT_V4_3_RC1.md",
        "docs/RELEASE_CHECKLIST_V4_3_RC1.md",
        "docs/V4_3_RC1_READINESS_REPORT.md",
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    assert "Production Readiness Validation" in gates
    assert "Release Compatibility Validation" in gates
    assert "Performance Regression Validation" in gates
    assert "Documentation Validation" in gates


def test_v4_3_rc1_updated_documentation_links_are_resolvable() -> None:
    documents = (
        ROOT / "README.md",
        ROOT / "RELEASE_V4_3_RC1.md",
        ROOT / "docs/ARCHITECTURE_SUMMARY_V4_3_RC1.md",
        ROOT / "docs/COMPATIBILITY_V4_3_RC1.md",
        ROOT / "docs/WORKFLOW_REGRESSION_V4_3_RC1.md",
        ROOT / "docs/BENCHMARK_V4_3_RC1.md",
        ROOT / "docs/SECURITY_AUDIT_V4_3_RC1.md",
        ROOT / "docs/RELEASE_CHECKLIST_V4_3_RC1.md",
        ROOT / "docs/V4_3_RC1_READINESS_REPORT.md",
    )

    for document in documents:
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", document.read_text(encoding="utf-8")):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            assert (document.parent / link).exists(), f"{document}: broken link to {link}"
