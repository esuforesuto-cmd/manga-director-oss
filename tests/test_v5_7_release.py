"""Final-release contracts for the stable v5.7 Production Platform."""

from __future__ import annotations

import json
import re
from pathlib import Path

from typer.testing import CliRunner

import manga_director
from manga_director import plugins, production
from manga_director.api import ObservabilityApplication
from manga_director.api.observability import create_observability_app
from manga_director.cli.app import app
from manga_director.mcp import McpServer

ROOT = Path(__file__).resolve().parents[1]


def _application() -> ObservabilityApplication:
    return ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type,return-value]
        diagnostics=lambda: None,  # type: ignore[arg-type,return-value]
        repository_check=lambda: None,  # type: ignore[arg-type,return-value]
    )


def test_v5_7_final_version_is_canonical_for_package_openapi_mcp_frontend_and_sbom() -> None:
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
    assert frontend["version"] == "6.0.0"
    assert lockfile["version"] == frontend["version"]
    assert lockfile["packages"][""]["version"] == frontend["version"]
    assert sbom["packages"][0]["versionInfo"] == manga_director.__version__


def test_v5_7_final_freezes_additive_platform_plugin_and_workspace_api_surfaces() -> None:
    production_exports = (
        "V57ProductionPlatformFoundationService",
        "V57ProductionWorkspaceService",
        "V57ProductionOrchestrator",
        "AutomationPipelineDTO",
        "AutomationPipelineReport",
        "V57EventBusEventDTO",
        "V57EventBusReport",
        "PluginRuntimeFoundation",
        "PluginLifecycleDescriptorDTO",
        "ProductionOrchestratorReport",
        "ProductionTemplateDTO",
        "ResourceAllocationDTO",
    )
    plugin_exports = (
        "Plugin",
        "PluginContribution",
        "PluginDiscovery",
        "PluginLoader",
        "PluginManager",
        "PluginManifest",
        "PluginRegistry",
        "PluginStatus",
        "PluginType",
    )

    assert all(hasattr(production, name) for name in production_exports)
    assert all(hasattr(plugins, name) for name in plugin_exports)


def test_v5_7_final_preserves_existing_cli_fastapi_mcp_and_web_contracts() -> None:
    initialized = McpServer(None, None, None).handle(  # type: ignore[arg-type]
        {"jsonrpc": "2.0", "id": 1, "method": "initialize"}
    )
    package = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))

    assert CliRunner().invoke(app, ["--help"]).exit_code == 0
    assert {"/health", "/diagnostics", "/repository/check"} <= {
        route.path for route in create_observability_app(_application()).routes
    }
    assert initialized is not None
    assert initialized["result"]["serverInfo"]["version"] == manga_director.__version__
    assert package["name"] == "manga-director-web"


def test_v5_7_final_release_assets_and_documentation_links_are_available() -> None:
    assets = (
        "RELEASE_V5_7.md",
        "docs/V5_7_RELEASE_READY_REPORT.md",
        "docs/FINAL_QUALITY_GATE_REPORT.md",
        "docs/PLATFORM_API_REFERENCE.md",
        "docs/PLUGIN_API_REFERENCE.md",
        "docs/WORKSPACE_SPECIFICATION.md",
        "docs/PERFORMANCE_BASELINE_V5_7.md",
        "docs/MIGRATION_V5_7.md",
        "docs/GITHUB_RELEASE_V5_7.md",
    )

    assert all((ROOT / asset).is_file() for asset in assets)
    for asset in assets:
        document = ROOT / asset
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", document.read_text(encoding="utf-8")):
            if not link.startswith(("http://", "https://", "mailto:")):
                assert (document.parent / link).exists(), f"{document}: broken link to {link}"
