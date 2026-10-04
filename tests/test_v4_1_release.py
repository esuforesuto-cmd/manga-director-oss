"""Stable v4.1 release metadata and Multi-Agent Platform contracts."""

from __future__ import annotations

import json
import re
from pathlib import Path

import manga_director
from manga_director.api import ObservabilityApplication
from manga_director.api.observability import create_observability_app
from manga_director.mcp import McpServer
from manga_director.production import (
    AgentRegistryRepository,
    V41AgentFoundationService,
    V41OrchestrationService,
    V41PlatformAssuranceService,
)

ROOT = Path(__file__).resolve().parents[1]


def test_v4_1_release_uses_one_canonical_version() -> None:
    sbom = json.loads((ROOT / "docs/SBOM.spdx.json").read_text(encoding="utf-8"))
    frontend = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    release = (ROOT / "RELEASE_V4_1.md").read_text(encoding="utf-8")
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
    assert "v4.1.0" in release


def test_v4_1_multi_agent_exports_are_additive_and_registry_remains_local() -> None:
    registry = AgentRegistryRepository()

    assert registry.list() == ()
    assert isinstance(V41AgentFoundationService(registry), V41AgentFoundationService)
    assert isinstance(V41OrchestrationService(registry), V41OrchestrationService)
    assert isinstance(V41PlatformAssuranceService(registry), V41PlatformAssuranceService)


def test_v4_1_final_assets_and_documentation_links_are_available() -> None:
    assets = (
        "RELEASE_V4_1.md",
        "docs/MIGRATION_V4_1.md",
        "docs/COMPATIBILITY_V4_1.md",
        "docs/MULTI_AGENT_ARCHITECTURE_SUMMARY_V4_1.md",
        "docs/WORKFLOW_REGRESSION_V4_1.md",
        "docs/BENCHMARK_V4_1.md",
        "docs/SECURITY_AUDIT_V4_1.md",
        "docs/PACKAGE_AUDIT_V4_1.md",
        "docs/RELEASE_CHECKLIST_V4_1.md",
        "docs/V4_1_RELEASE_READY_REPORT.md",
        "docs/GITHUB_RELEASE_V4_1.md",
        "docs/DEPENDENCY_LICENSE_REPORT.md",
        "docs/SBOM.spdx.json",
    )
    documents = (
        ROOT / "RELEASE_V4_1.md",
        *(ROOT / asset for asset in assets if asset.endswith(".md")),
    )
    gates = (ROOT / "docs/V4_QUALITY_GATES.md").read_text(encoding="utf-8")

    assert all((ROOT / asset).is_file() for asset in assets)
    for document in documents:
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", document.read_text(encoding="utf-8")):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            assert (document.parent / link).exists(), f"{document}: broken link to {link}"
    assert "Release Readiness" in gates
    assert "OSS Readiness" in gates
    assert "Backward Compatibility" in gates
    assert "Documentation Quality" in gates
    assert "Package Quality" in gates
