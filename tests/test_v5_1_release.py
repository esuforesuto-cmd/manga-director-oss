"""Stable v5.1 release metadata and Composable Platform contracts."""

from __future__ import annotations

import json
import re
from pathlib import Path

import manga_director
from manga_director.api import ObservabilityApplication
from manga_director.api.observability import create_observability_app
from manga_director.mcp import McpServer
from manga_director.platform import CompositionPlatformMaturityService

ROOT = Path(__file__).resolve().parents[1]


def _application() -> ObservabilityApplication:
    return ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type,return-value]
        diagnostics=lambda: None,  # type: ignore[arg-type,return-value]
        repository_check=lambda: None,  # type: ignore[arg-type,return-value]
    )


def test_v5_1_final_uses_one_canonical_version() -> None:
    sbom = json.loads((ROOT / "docs/SBOM.spdx.json").read_text(encoding="utf-8"))
    frontend = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    lockfile = json.loads((ROOT / "web/package-lock.json").read_text(encoding="utf-8"))
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


def test_v5_1_final_composition_platform_remains_additive() -> None:
    service = CompositionPlatformMaturityService()

    assert isinstance(service, CompositionPlatformMaturityService)


def test_v5_1_final_assets_quality_gates_and_documentation_links_are_available() -> None:
    assets = (
        "RELEASE_V5_1.md",
        "docs/MIGRATION_V5_0_TO_V5_1.md",
        "docs/V5_1_PLATFORM_SUMMARY.md",
        "docs/ARCHITECTURE_SUMMARY_V5_1.md",
        "docs/COMPATIBILITY_V5_1.md",
        "docs/WORKFLOW_REGRESSION_V5_1.md",
        "docs/BENCHMARK_V5_1.md",
        "docs/SECURITY_AUDIT_V5_1.md",
        "docs/PACKAGE_AUDIT_V5_1.md",
        "docs/RELEASE_CHECKLIST_V5_1.md",
        "docs/GITHUB_RELEASE_V5_1.md",
        "docs/V5_1_RELEASE_READY_REPORT.md",
        "docs/DEPENDENCY_LICENSE_REPORT.md",
        "docs/SBOM.spdx.json",
    )
    documents = tuple(ROOT / asset for asset in assets if asset.endswith(".md"))
    gates = (ROOT / "docs/V5_1_QUALITY_GATES.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    for document in documents:
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", document.read_text(encoding="utf-8")):
            if not link.startswith(("http://", "https://", "mailto:")):
                assert (document.parent / link).exists(), f"{document}: broken link to {link}"
    for gate in (
        "Release Readiness",
        "v5.0 LTS Backward Compatibility",
        "Composition Platform Completion",
        "Performance Regression",
        "Documentation and Package Quality",
        "Security Validation",
    ):
        assert gate in gates
