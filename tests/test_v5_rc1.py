"""RC1 contracts for the v5 One Creative Platform."""

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
from manga_director.platform import (
    UnifiedContextReferenceDTO,
    UnifiedPlatformMaturityService,
)
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "pilot-1", "storyboard": {"panels": []}},
        state=PageState.PROMPT_BUILT,
        artifacts={"storyboard": {"panels": []}, "prompt": {"text": "redacted"}},
        metadata={"provenance": "human", "workflow_history": [{"step": "prompt"}]},
    )


def _references() -> tuple[UnifiedContextReferenceDTO, ...]:
    return (
        UnifiedContextReferenceDTO(
            domain="workspace",
            context_id="workspace-1",
            source_module="workspace",
            source_reference="workspace:workspace-1",
        ),
        UnifiedContextReferenceDTO(
            domain="knowledge",
            context_id="knowledge-1",
            source_module="knowledge",
            source_reference="knowledge:knowledge-1",
        ),
        UnifiedContextReferenceDTO(
            domain="agent",
            context_id="agent-1",
            source_module="agents",
            source_reference="agent:agent-1",
        ),
        UnifiedContextReferenceDTO(
            domain="production",
            context_id="production-1",
            source_module="production",
            source_reference="production:production-1",
        ),
    )


def _application() -> ObservabilityApplication:
    return ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type,return-value]
        diagnostics=lambda: None,  # type: ignore[arg-type,return-value]
        repository_check=lambda: None,  # type: ignore[arg-type,return-value]
    )


def test_v5_rc1_version_is_canonical_for_package_openapi_mcp_frontend_and_sbom() -> None:
    frontend = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    lockfile = json.loads((ROOT / "web/package-lock.json").read_text(encoding="utf-8"))
    sbom = json.loads((ROOT / "docs/SBOM.spdx.json").read_text(encoding="utf-8"))
    initialized = McpServer(None, None, None).handle(  # type: ignore[arg-type]
        {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    )

    assert manga_director.__version__ == "6.0.0"
    assert create_observability_app(_application()).version == manga_director.__version__
    assert initialized is not None
    assert initialized["result"]["serverInfo"]["version"] == manga_director.__version__
    assert frontend["version"] == manga_director.__version__.replace("rc", "-rc.")
    assert lockfile["version"] == frontend["version"]
    assert lockfile["packages"][""]["version"] == frontend["version"]
    assert sbom["packages"][0]["versionInfo"] == manga_director.__version__


def test_v5_rc1_platform_e2e_preserves_workflow_and_owner_boundaries() -> None:
    report = UnifiedPlatformMaturityService().report("pilot", _context(), _references())
    repository = InMemoryRepository()
    repository.save(
        Project(
            id="pilot",
            title="Pilot",
            chapters=[Chapter(id="one", title="One", page_numbers=[1])],
            pages=[Page(page_number=1, storyboard={"panels": []})],
        )
    )
    reloaded = repository.load("pilot")

    assert report.planning_only is True
    assert report.dashboard.context_intelligence.context.page_count == 1
    assert report.governance.policy.state_machine_authoritative is True
    assert report.governance.policy.policy_enforced is False
    assert report.observability.monitoring_started is False
    assert report.reliability.automatic_recovery_taken is False
    assert report.lifecycle.lifecycle_owner_transferred is False
    assert report.developer_experience.configuration_changed is False
    assert reloaded is not None
    assert reloaded.pages[0].storyboard == {"panels": []}


def test_v5_rc1_retains_existing_cli_contract() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "one-page-at-a-time" in result.stdout


def test_v5_rc1_assets_quality_gates_and_documentation_links_are_available() -> None:
    assets = (
        "RELEASE_V5_RC1.md",
        "docs/ARCHITECTURE_SUMMARY_V5_RC1.md",
        "docs/COMPATIBILITY_V5_RC1.md",
        "docs/WORKFLOW_REGRESSION_V5_RC1.md",
        "docs/BENCHMARK_V5_RC1.md",
        "docs/SECURITY_AUDIT_V5_RC1.md",
        "docs/PACKAGE_AUDIT_V5_RC1.md",
        "docs/RELEASE_CHECKLIST_V5_RC1.md",
        "docs/V5_RC1_READINESS_REPORT.md",
        "docs/GITHUB_RELEASE_V5_RC1.md",
        "docs/DEPENDENCY_LICENSE_REPORT.md",
        "docs/SBOM.spdx.json",
    )
    documents = tuple(ROOT / asset for asset in assets if asset.endswith(".md"))
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    for document in documents:
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", document.read_text(encoding="utf-8")):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            assert (document.parent / link).exists(), f"{document}: broken link to {link}"
    for gate in (
        "RC Readiness Validation",
        "Release Compatibility Validation",
        "Performance Regression Validation",
        "Documentation Validation",
        "Unified Platform End-to-End Validation",
    ):
        assert gate in gates
