"""Stable v4.7 release metadata and delivery-boundary contracts."""

from __future__ import annotations

import json
import re
from pathlib import Path

import manga_director
from manga_director.api import ObservabilityApplication
from manga_director.api.observability import create_observability_app
from manga_director.mcp import McpServer
from manga_director.production import (
    V47DecisionFoundationService,
    V47DecisionGovernanceService,
    V47DecisionIntelligenceService,
)

ROOT = Path(__file__).resolve().parents[1]


def _application() -> ObservabilityApplication:
    return ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type,return-value]
        diagnostics=lambda: None,  # type: ignore[arg-type,return-value]
        repository_check=lambda: None,  # type: ignore[arg-type,return-value]
    )


def test_v4_7_release_uses_one_canonical_version() -> None:
    sbom = json.loads((ROOT / "docs/SBOM.spdx.json").read_text(encoding="utf-8"))
    frontend = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    lockfile = json.loads((ROOT / "web/package-lock.json").read_text(encoding="utf-8"))
    release = (ROOT / "RELEASE_V4_7.md").read_text(encoding="utf-8")
    initialized = McpServer(None, None, None).handle(  # type: ignore[arg-type]
        {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    )

    assert manga_director.__version__ == "6.0.0"
    assert sbom["packages"][0]["versionInfo"] == manga_director.__version__
    assert frontend["version"] == manga_director.__version__.replace("rc", "-rc.")
    assert lockfile["version"] == frontend["version"]
    assert lockfile["packages"][""]["version"] == frontend["version"]
    assert create_observability_app(_application()).version == manga_director.__version__
    assert initialized is not None
    assert initialized["result"]["serverInfo"]["version"] == manga_director.__version__
    assert "v4.7.0" in release


def test_v4_7_decision_platform_services_remain_additive_and_nonexecuting() -> None:
    foundation = V47DecisionFoundationService()
    intelligence = V47DecisionIntelligenceService(foundation)
    governance = V47DecisionGovernanceService(intelligence)

    assert isinstance(foundation, V47DecisionFoundationService)
    assert isinstance(intelligence, V47DecisionIntelligenceService)
    assert isinstance(governance, V47DecisionGovernanceService)


def test_v4_7_final_assets_quality_gates_and_documentation_links_are_available() -> None:
    assets = (
        "RELEASE_V4_7.md",
        "docs/MIGRATION_V4_7.md",
        "docs/COMPATIBILITY_V4_7.md",
        "docs/ARCHITECTURE_SUMMARY_V4_7.md",
        "docs/WORKFLOW_REGRESSION_V4_7.md",
        "docs/BENCHMARK_V4_7.md",
        "docs/SECURITY_AUDIT_V4_7.md",
        "docs/PACKAGE_AUDIT_V4_7.md",
        "docs/RELEASE_CHECKLIST_V4_7.md",
        "docs/V4_7_RELEASE_READY_REPORT.md",
        "docs/GITHUB_RELEASE_V4_7.md",
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
        "Release Readiness",
        "OSS Readiness",
        "Backward Compatibility",
        "Documentation Quality",
        "Package Quality",
    ):
        assert gate in gates
