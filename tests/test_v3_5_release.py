"""Stable-release metadata and delivery-boundary contracts for v3.5."""

from __future__ import annotations

import json
import re
from pathlib import Path

import manga_director
from manga_director.api import ObservabilityApplication
from manga_director.api.observability import create_observability_app
from manga_director.mcp import McpServer

ROOT = Path(__file__).resolve().parents[1]


def test_v3_5_release_uses_one_canonical_version() -> None:
    sbom = json.loads((ROOT / "docs/SBOM.spdx.json").read_text(encoding="utf-8"))
    frontend = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    release = (ROOT / "RELEASE_V3_5.md").read_text(encoding="utf-8")
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
    )
    initialized = McpServer(None, None, None).handle(  # type: ignore[arg-type]
        {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    )

    assert manga_director.__version__ == "6.0.0"
    assert sbom["packages"][0]["versionInfo"] == manga_director.__version__
    assert frontend["version"] == manga_director.__version__.replace("rc", "-rc.")
    assert create_observability_app(application).version == manga_director.__version__
    assert initialized is not None
    assert initialized["result"]["serverInfo"]["version"] == manga_director.__version__
    assert "v3.5.0" in release


def test_v3_5_final_assets_and_documentation_links_are_available() -> None:
    assets = (
        "RELEASE_V3_5.md",
        "docs/MIGRATION_V3_5.md",
        "docs/COMPATIBILITY_V3_5.md",
        "docs/ARCHITECTURE_SUMMARY_V3_5.md",
        "docs/WORKFLOW_REGRESSION_V3_5.md",
        "docs/BENCHMARK_V3_5.md",
        "docs/SECURITY_AUDIT_V3_5.md",
        "docs/PACKAGE_AUDIT_V3_5.md",
        "docs/RELEASE_CHECKLIST_V3_5.md",
        "docs/V3_5_RELEASE_READY_REPORT.md",
        "docs/GITHUB_RELEASE_V3_5.md",
        "docs/DEPENDENCY_LICENSE_REPORT.md",
        "docs/SBOM.spdx.json",
    )
    documents = tuple(ROOT / asset for asset in assets if asset.endswith(".md"))

    assert all((ROOT / asset).is_file() for asset in assets)
    for document in documents:
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", document.read_text(encoding="utf-8")):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            assert (document.parent / link).exists(), f"{document}: broken link to {link}"
