"""RC1 contracts for the v5.2 Creative Automation Framework."""

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
    AutomationEngineFoundation,
    AutomationEventDTO,
    AutomationPlatformMaturityService,
    AutomationRegistryFoundation,
    AutomationRequestDTO,
    AutomationRuleDTO,
    EventBusFoundation,
    WorkflowTemplateDTO,
)
from manga_director.repositories import InMemoryRepository

ROOT = Path(__file__).resolve().parents[1]


def _application() -> ObservabilityApplication:
    return ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type,return-value]
        diagnostics=lambda: None,  # type: ignore[arg-type,return-value]
        repository_check=lambda: None,  # type: ignore[arg-type,return-value]
    )


def _service_and_request() -> tuple[AutomationPlatformMaturityService, AutomationRequestDTO]:
    template = WorkflowTemplateDTO(
        template_id="storyboard-review",
        title="Storyboard Review",
        owner="creative-operations",
        page_reference="page-001",
        required_evidence=("storyboard", "quality-review"),
    )
    rule = AutomationRuleDTO(
        rule_id="review-ready",
        title="Review Readiness",
        owner="creative-operations",
        required_evidence=("storyboard", "quality-review"),
    )
    event = AutomationEventDTO(
        event_id="review-completed",
        event_type="quality-review.completed",
        producer="quality-review",
        page_reference="page-001",
        provenance="caller-supplied",
    )
    engine = AutomationEngineFoundation(
        registry=AutomationRegistryFoundation((template,), (rule,)),
        event_bus=EventBusFoundation((event,)),
    )
    return AutomationPlatformMaturityService(engine), AutomationRequestDTO(
        template_id=template.template_id,
        rule_id=rule.rule_id,
        event_id=event.event_id,
        evidence_types=("storyboard", "quality-review"),
        approval_boundary="editor-review",
    )


def test_v5_2_rc1_version_is_canonical_for_package_openapi_mcp_frontend_and_sbom() -> None:
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


def test_v5_2_rc1_automation_e2e_preserves_workflow_and_repository_contracts() -> None:
    service, request = _service_and_request()
    report = service.report(request)
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

    assert report.dashboard.automation.health == "ready_for_human_review"
    assert report.governance.policy.state_machine_authoritative is True
    assert report.governance.policy.policy_enforced is False
    assert report.observability.monitoring_started is False
    assert report.lifecycle.lifecycle.lifecycle_transitioned is False
    assert report.reliability.runtime_reconfigured is False
    assert report.automatic_action_taken is False
    assert reloaded is not None
    assert len(reloaded.pages) == 1
    assert reloaded.pages[0].storyboard == {"panels": []}
    assert PageState.STORYBOARDED.value == "Storyboarded"


def test_v5_2_rc1_retains_existing_cli_contract() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "one-page-at-a-time" in result.stdout


def test_v5_2_rc1_assets_quality_gates_and_documentation_links_are_available() -> None:
    assets = (
        "RELEASE_V5_2_RC1.md",
        "docs/ARCHITECTURE_SUMMARY_V5_2_RC1.md",
        "docs/COMPATIBILITY_V5_2_RC1.md",
        "docs/WORKFLOW_REGRESSION_V5_2_RC1.md",
        "docs/BENCHMARK_V5_2_RC1.md",
        "docs/SECURITY_AUDIT_V5_2_RC1.md",
        "docs/PACKAGE_AUDIT_V5_2_RC1.md",
        "docs/RELEASE_CHECKLIST_V5_2_RC1.md",
        "docs/V5_2_RC1_READINESS_REPORT.md",
        "docs/GITHUB_RELEASE_V5_2_RC1.md",
        "docs/DEPENDENCY_LICENSE_REPORT.md",
        "docs/SBOM.spdx.json",
    )
    documents = tuple(ROOT / asset for asset in assets if asset.endswith(".md"))
    gates = (ROOT / "docs/V5_2_QUALITY_GATES.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    for document in documents:
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", document.read_text(encoding="utf-8")):
            if not link.startswith(("http://", "https://", "mailto:")):
                assert (document.parent / link).exists(), f"{document}: broken link to {link}"
    for gate in (
        "RC Readiness Validation",
        "Release Compatibility Validation",
        "Performance Regression Validation",
        "Documentation Validation",
        "Automation Framework End-to-End Validation",
    ):
        assert gate in gates
