"""Release-facing contracts that guard public metadata and delivery entry points."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

import manga_director
from manga_director.api.observability import create_observability_app
from manga_director.cli.app import app
from manga_director.mcp import McpServer

ROOT = Path(__file__).resolve().parents[1]


class _ObservabilityRoutesStub:
    def __getattr__(self, _: str) -> Any:
        return lambda: {}


def test_mcp_version_uses_the_package_version() -> None:
    server = McpServer(tool_registry=None, resources=None, prompts=None)  # type: ignore[arg-type]

    response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})

    assert response is not None
    assert response["result"]["serverInfo"]["version"] == manga_director.__version__


def test_openapi_version_uses_the_package_version() -> None:
    observability_app = create_observability_app(_ObservabilityRoutesStub())  # type: ignore[arg-type]

    assert observability_app.version == manga_director.__version__


def test_mcp_masks_unexpected_transport_errors() -> None:
    server = McpServer(tool_registry=None, resources=None, prompts=None)  # type: ignore[arg-type]

    response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "unsupported"})

    assert response is not None
    assert response["error"]["message"] == "Request could not be completed."


def test_cli_help_starts_without_project_configuration() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "Headless" in result.output


def test_package_version_and_typed_marker_are_present() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert metadata["project"]["dynamic"] == ["version"]
    assert metadata["tool"]["hatch"]["version"]["path"] == "src/manga_director/_version.py"
    assert (ROOT / "src" / "manga_director" / "py.typed").is_file()


def test_frontend_release_version_is_aligned() -> None:
    frontend_package = json.loads((ROOT / "web" / "package.json").read_text(encoding="utf-8"))
    lockfile = json.loads((ROOT / "web" / "package-lock.json").read_text(encoding="utf-8"))

    expected_frontend_version = manga_director.__version__.replace("rc", "-rc.")
    assert frontend_package["version"] == expected_frontend_version
    assert lockfile["version"] == frontend_package["version"]
    assert lockfile["packages"][""]["version"] == frontend_package["version"]


def test_release_assets_and_sbom_match_the_package() -> None:
    required_assets = [
        "CHANGELOG.md",
        "CODE_OF_CONDUCT.md",
        ".github/CODEOWNERS",
        "CONTRIBUTING.md",
        "GOVERNANCE.md",
        "LICENSE",
        "MAINTAINERS.md",
        "SECURITY.md",
        "SUPPORTED_VERSIONS.md",
        "docs/DEPENDENCY_LICENSE_REPORT.md",
        "docs/RELEASE_CHECKLIST_V2.md",
        "docs/COMPATIBILITY_V2_1.md",
        "docs/COMPATIBILITY_V2_2_RC1.md",
        "docs/COMPATIBILITY_V2_2.md",
        "docs/COMPATIBILITY_V2_3_RC1.md",
        "docs/COMPATIBILITY_V2_3.md",
        "docs/BENCHMARK_V2_1.md",
        "docs/BENCHMARK_V2_2.md",
        "docs/ARCHITECTURE_SUMMARY_V2_2.md",
        "docs/V2_2_RC1_READINESS_REPORT.md",
        "docs/V2_2_RELEASE_READY_REPORT.md",
        "docs/BENCHMARK_V2_3_RC1.md",
        "docs/ARCHITECTURE_SUMMARY_V2_3_RC1.md",
        "docs/RELEASE_CHECKLIST_V2_3_RC1.md",
        "docs/RELEASE_CHECKLIST_V2_3.md",
        "docs/V2_3_RC1_READINESS_REPORT.md",
        "docs/V2_3_RELEASE_READY_REPORT.md",
        "docs/ARCHITECTURE_SUMMARY_V2_3.md",
        "docs/COMPATIBILITY_V2_4_RC1.md",
        "docs/COMPATIBILITY_V2_4.md",
        "docs/BENCHMARK_V2_4_RC1.md",
        "docs/ARCHITECTURE_SUMMARY_V2_4_RC1.md",
        "docs/ARCHITECTURE_SUMMARY_V2_4.md",
        "docs/RELEASE_CHECKLIST_V2_4_RC1.md",
        "docs/RELEASE_CHECKLIST_V2_4.md",
        "docs/V2_4_RC1_READINESS_REPORT.md",
        "docs/V2_4_RELEASE_READY_REPORT.md",
        "docs/MIGRATION_V2_4.md",
        "docs/PRODUCTION_DEPLOYMENT_V2_4.md",
        "docs/OPERATIONS_V2_4.md",
        "docs/ROADMAP_v2_5.md",
        "docs/GITHUB_V2_5_PLAN.md",
        "docs/PRODUCTION_BACKLOG_V2_5.md",
        "docs/OPERATIONS_BEST_PRACTICES.md",
        "docs/QUALITY_ASSURANCE.md",
        "docs/PROVIDER_SELECTION.md",
        "docs/BACKEND_SELECTION.md",
        "docs/UPGRADE_POLICY.md",
        "docs/V2_5_DEVELOPMENT_PLANNING_REPORT.md",
        "docs/QUALITY_PIPELINE.md",
        "docs/REPOSITORY_MAINTENANCE.md",
        "docs/DEVELOPER_PRODUCTIVITY.md",
        "docs/RELEASE_VALIDATION.md",
        "docs/V2_5_ITERATION_1_QUALITY_AUTOMATION_REPORT.md",
        "docs/OBSERVABILITY_REFERENCE.md",
        "docs/DIAGNOSTICS_REFERENCE.md",
        "docs/PERFORMANCE_ANALYSIS.md",
        "docs/OPERATIONS_AUTOMATION.md",
        "docs/V2_5_ITERATION_2_OBSERVABILITY_PERFORMANCE_REPORT.md",
        "docs/OSS_READINESS.md",
        "docs/RELEASE_PROCESS.md",
        "docs/MAINTENANCE_GUIDE.md",
        "docs/DEPENDENCY_POLICY.md",
        "docs/V2_5_ITERATION_3_RELIABILITY_OSS_READINESS_REPORT.md",
        "docs/COMPATIBILITY_V2_5_RC1.md",
        "docs/ARCHITECTURE_SUMMARY_V2_5_RC1.md",
        "docs/BENCHMARK_V2_5_RC1.md",
        "docs/RELEASE_CHECKLIST_V2_5_RC1.md",
        "docs/V2_5_RC1_READINESS_REPORT.md",
        "docs/COMPATIBILITY_V2_5.md",
        "docs/ARCHITECTURE_SUMMARY_V2_5.md",
        "docs/RELEASE_CHECKLIST_V2_5.md",
        "docs/MIGRATION_V2_5.md",
        "docs/PRODUCTION_DEPLOYMENT_V2_5.md",
        "docs/OPERATIONS_V2_5.md",
        "docs/V2_5_RELEASE_READY_REPORT.md",
        "docs/V2_5_QUALITY_REPORT.md",
        "docs/ROADMAP_v2_6.md",
        "docs/GITHUB_V2_6_PLAN.md",
        "docs/AI_WORKFLOW.md",
        "docs/PROVIDER_ORCHESTRATION.md",
        "docs/ENTERPRISE_OPERATIONS.md",
        "docs/AUTOMATION_PLANNING.md",
        "docs/UPGRADE_GUIDE_v2_6.md",
        "docs/V2_6_DEVELOPMENT_PLANNING_REPORT.md",
        "docs/WORKFLOW_PLANNING.md",
        "docs/WORKFLOW_INTELLIGENCE.md",
        "docs/PLANNING_DIAGNOSTICS.md",
        "docs/V2_6_ITERATION_1_WORKFLOW_INTELLIGENCE_REPORT.md",
        "docs/WORKFLOW_ANALYSIS.md",
        "docs/PROVIDER_OPTIMIZATION.md",
        "docs/ENTERPRISE_DIAGNOSTICS.md",
        "docs/OPERATIONAL_ANALYTICS.md",
        "docs/V2_6_ITERATION_2_WORKFLOW_ANALYTICS_REPORT.md",
        "docs/WORKFLOW_RELIABILITY.md",
        "docs/PROVIDER_GOVERNANCE.md",
        "docs/ENTERPRISE_READINESS.md",
        "docs/AI_WORKFLOW_DIAGNOSTICS.md",
        "docs/V2_6_ITERATION_3_AI_WORKFLOW_RELIABILITY_REPORT.md",
        "docs/COMPATIBILITY_V2_6_RC1.md",
        "docs/ARCHITECTURE_SUMMARY_V2_6_RC1.md",
        "docs/WORKFLOW_REGRESSION_V2_6_RC1.md",
        "docs/BENCHMARK_V2_6_RC1.md",
        "docs/SECURITY_AUDIT_V2_6_RC1.md",
        "docs/PACKAGE_AUDIT_V2_6_RC1.md",
        "docs/RELEASE_CHECKLIST_V2_6_RC1.md",
        "docs/V2_6_RC1_READINESS_REPORT.md",
        "docs/COMPATIBILITY_V2_6.md",
        "docs/ARCHITECTURE_SUMMARY_V2_6.md",
        "docs/BENCHMARK_V2_6.md",
        "docs/RELEASE_CHECKLIST_V2_6.md",
        "docs/MIGRATION_V2_6.md",
        "docs/PRODUCTION_DEPLOYMENT_V2_6.md",
        "docs/OPERATIONS_V2_6.md",
        "docs/AI_WORKFLOW_GUIDE_V2_6.md",
        "docs/V2_6_RELEASE_READY_REPORT.md",
        "docs/ROADMAP_v2_7.md",
        "docs/GITHUB_V2_7_PLAN.md",
        "docs/AI_DIRECTOR.md",
        "docs/KNOWLEDGE_MANAGEMENT.md",
        "docs/WORKFLOW_ORCHESTRATION.md",
        "docs/UPGRADE_GUIDE_v2_7.md",
        "docs/AI_DIRECTOR_BACKLOG_V2_7.md",
        "docs/KNOWLEDGE_BACKLOG_V2_7.md",
        "docs/AUTOMATION_BACKLOG_V2_7.md",
        "docs/V2_7_DEVELOPMENT_PLANNING_REPORT.md",
        "docs/DIRECTOR_FOUNDATION.md",
        "docs/KNOWLEDGE_INDEX.md",
        "docs/DECISION_TRACE.md",
        "docs/V2_7_ITERATION_1_AI_DIRECTOR_FOUNDATION_REPORT.md",
        "docs/KNOWLEDGE_INTELLIGENCE.md",
        "docs/DIRECTOR_ANALYSIS.md",
        "docs/WORKFLOW_OPTIMIZATION.md",
        "docs/ENTERPRISE_KNOWLEDGE.md",
        "docs/V2_7_ITERATION_2_KNOWLEDGE_INTELLIGENCE_REPORT.md",
        "docs/DIRECTOR_RELIABILITY.md",
        "docs/KNOWLEDGE_GOVERNANCE.md",
        "docs/ENTERPRISE_AI_READINESS.md",
        "docs/V2_7_ITERATION_3_AI_DIRECTOR_RELIABILITY_REPORT.md",
        "docs/COMPATIBILITY_V2_7_RC1.md",
        "docs/ARCHITECTURE_SUMMARY_V2_7_RC1.md",
        "docs/WORKFLOW_REGRESSION_V2_7_RC1.md",
        "docs/BENCHMARK_V2_7_RC1.md",
        "docs/SECURITY_AUDIT_V2_7_RC1.md",
        "docs/PACKAGE_AUDIT_V2_7_RC1.md",
        "docs/RELEASE_CHECKLIST_V2_7_RC1.md",
        "docs/V2_7_RC1_READINESS_REPORT.md",
        "docs/COMPATIBILITY_V2_7.md",
        "docs/ARCHITECTURE_SUMMARY_V2_7.md",
        "docs/BENCHMARK_V2_7.md",
        "docs/RELEASE_CHECKLIST_V2_7.md",
        "docs/MIGRATION_V2_7.md",
        "docs/PRODUCTION_DEPLOYMENT_V2_7.md",
        "docs/OPERATIONS_V2_7.md",
        "docs/AI_DIRECTOR_GUIDE_V2_7.md",
        "docs/KNOWLEDGE_GUIDE_V2_7.md",
        "docs/V2_7_RELEASE_READY_REPORT.md",
        "docs/VISION_v3.md",
        "docs/ARCHITECTURE_V3.md",
        "docs/V3_ARCHITECTURE.md",
        "docs/ROADMAP_v3.md",
        "docs/GITHUB_V3_PLAN.md",
        "docs/AI_DIRECTOR_PLATFORM.md",
        "docs/MULTI_AGENT.md",
        "docs/KNOWLEDGE_GRAPH.md",
        "docs/CREATIVE_PIPELINE.md",
        "docs/V3_BENCHMARK_PLAN.md",
        "docs/V3_DEVELOPMENT_PLANNING_REPORT.md",
        "docs/DIRECTOR_PLATFORM.md",
        "docs/CREATIVE_PLANNING.md",
        "docs/KNOWLEDGE_FOUNDATION.md",
        "docs/V3_ITERATION_1_FOUNDATION_REPORT.md",
        "docs/MULTI_AGENT_FOUNDATION.md",
        "docs/CREATIVE_KNOWLEDGE.md",
        "docs/DIRECTOR_INTELLIGENCE.md",
        "docs/REVIEW_PIPELINE.md",
        "docs/V3_ITERATION_2_MULTI_AGENT_FOUNDATION_REPORT.md",
        "docs/DIRECTOR_RELIABILITY_V3.md",
        "docs/CREATIVE_GOVERNANCE.md",
        "docs/KNOWLEDGE_INTEGRITY.md",
        "docs/PRODUCTION_READINESS.md",
        "docs/V3_ITERATION_3_PRODUCTION_READINESS_REPORT.md",
        "docs/COMPATIBILITY_V3_RC1.md",
        "docs/ARCHITECTURE_SUMMARY_V3_RC1.md",
        "docs/WORKFLOW_REGRESSION_V3_RC1.md",
        "docs/BENCHMARK_V3_RC1.md",
        "docs/SECURITY_AUDIT_V3_RC1.md",
        "docs/PACKAGE_AUDIT_V3_RC1.md",
        "docs/RELEASE_CHECKLIST_V3_RC1.md",
        "docs/MIGRATION_V3_RC1.md",
        "docs/V3_RC1_READINESS_REPORT.md",
        "docs/COMPATIBILITY_V3.md",
        "docs/ARCHITECTURE_SUMMARY_V3.md",
        "docs/BENCHMARK_V3.md",
        "docs/RELEASE_CHECKLIST_V3.md",
        "docs/MIGRATION_V3.md",
        "docs/PRODUCTION_DEPLOYMENT_V3.md",
        "docs/OPERATIONS_V3.md",
        "docs/AI_DIRECTOR_PLATFORM_GUIDE_V3.md",
        "docs/CREATIVE_PIPELINE_GUIDE_V3.md",
        "docs/KNOWLEDGE_GUIDE_V3.md",
        "docs/V3_RELEASE_READY_REPORT.md",
        "docs/VISION_v3_1.md",
        "docs/ARCHITECTURE_V3_1.md",
        "docs/V3_1_ARCHITECTURE.md",
        "docs/CREATIVE_COLLABORATION.md",
        "docs/KNOWLEDGE_EVOLUTION.md",
        "docs/OPERATIONS_PLATFORM.md",
        "docs/ROADMAP_v3_1.md",
        "docs/GITHUB_V3_1_PLAN.md",
        "docs/V3_1_BENCHMARK_PLAN.md",
        "docs/V3_1_DEVELOPMENT_PLANNING_REPORT.md",
        "docs/CREATIVE_COLLABORATION_FOUNDATION.md",
        "docs/KNOWLEDGE_EVOLUTION_FOUNDATION.md",
        "docs/OPERATIONS_FOUNDATION.md",
        "docs/DEVELOPER_PRODUCTIVITY.md",
        "docs/V3_1_ITERATION_1_FOUNDATION_REPORT.md",
        "docs/CREATIVE_REVIEW.md",
        "docs/KNOWLEDGE_ANALYTICS.md",
        "docs/OPERATIONS_INTELLIGENCE.md",
        "docs/DEVELOPER_EXPERIENCE.md",
        "docs/V3_1_ITERATION_2_CREATIVE_REVIEW_REPORT.md",
        "docs/CREATIVE_GOVERNANCE_V3_1.md",
        "docs/KNOWLEDGE_RELIABILITY.md",
        "docs/OPERATIONAL_READINESS.md",
        "docs/RELEASE_QUALITY.md",
        "docs/V3_1_ITERATION_3_RELEASE_QUALITY_REPORT.md",
        "docs/COMPATIBILITY_V3_1_RC1.md",
        "docs/ARCHITECTURE_SUMMARY_V3_1_RC1.md",
        "docs/WORKFLOW_REGRESSION_V3_1_RC1.md",
        "docs/BENCHMARK_V3_1_RC1.md",
        "docs/SECURITY_AUDIT_V3_1_RC1.md",
        "docs/PACKAGE_AUDIT_V3_1_RC1.md",
        "docs/RELEASE_CHECKLIST_V3_1_RC1.md",
        "docs/MIGRATION_V3_1_RC1.md",
        "docs/V3_1_RC1_READINESS_REPORT.md",
        "docs/COMPATIBILITY_V3_1.md",
        "docs/ARCHITECTURE_SUMMARY_V3_1.md",
        "docs/WORKFLOW_REGRESSION_V3_1.md",
        "docs/BENCHMARK_V3_1.md",
        "docs/SECURITY_AUDIT_V3_1.md",
        "docs/PACKAGE_AUDIT_V3_1.md",
        "docs/RELEASE_CHECKLIST_V3_1.md",
        "docs/MIGRATION_V3_1.md",
        "docs/V3_1_RELEASE_READY_REPORT.md",
        "docs/COMPATIBILITY_V3_2_RC1.md",
        "docs/ARCHITECTURE_SUMMARY_V3_2_RC1.md",
        "docs/WORKFLOW_REGRESSION_V3_2_RC1.md",
        "docs/BENCHMARK_V3_2_RC1.md",
        "docs/SECURITY_AUDIT_V3_2_RC1.md",
        "docs/PACKAGE_AUDIT_V3_2_RC1.md",
        "docs/MIGRATION_V3_2_RC1.md",
        "docs/RELEASE_CHECKLIST_V3_2_RC1.md",
        "docs/V3_2_RC1_READINESS_REPORT.md",
        "docs/COMPATIBILITY_V3_2.md",
        "docs/ARCHITECTURE_SUMMARY_V3_2.md",
        "docs/WORKFLOW_REGRESSION_V3_2.md",
        "docs/BENCHMARK_V3_2.md",
        "docs/SECURITY_AUDIT_V3_2.md",
        "docs/PACKAGE_AUDIT_V3_2.md",
        "docs/MIGRATION_V3_2.md",
        "docs/RELEASE_CHECKLIST_V3_2.md",
        "docs/V3_2_RELEASE_READY_REPORT.md",
        "docs/PRODUCTION_DEPLOYMENT_V3_2.md",
        "docs/OPERATIONS_V3_2.md",
        "docs/CREATIVE_STUDIO_GUIDE_V3_2.md",
        "docs/ASSET_INTELLIGENCE_GUIDE_V3_2.md",
        "docs/WORKFLOW_PROFILES_GUIDE_V3_2.md",
        "docs/COMPATIBILITY_V3_3_RC1.md",
        "docs/ARCHITECTURE_SUMMARY_V3_3_RC1.md",
        "docs/WORKFLOW_REGRESSION_V3_3_RC1.md",
        "docs/BENCHMARK_V3_3_RC1.md",
        "docs/SECURITY_AUDIT_V3_3_RC1.md",
        "docs/PACKAGE_AUDIT_V3_3_RC1.md",
        "docs/MIGRATION_V3_3_RC1.md",
        "docs/RELEASE_CHECKLIST_V3_3_RC1.md",
        "docs/V3_3_RC1_READINESS_REPORT.md",
        "docs/COMPATIBILITY_V3_3.md",
        "docs/ARCHITECTURE_SUMMARY_V3_3.md",
        "docs/WORKFLOW_REGRESSION_V3_3.md",
        "docs/BENCHMARK_V3_3.md",
        "docs/SECURITY_AUDIT_V3_3.md",
        "docs/PACKAGE_AUDIT_V3_3.md",
        "docs/MIGRATION_V3_3.md",
        "docs/RELEASE_CHECKLIST_V3_3.md",
        "docs/V3_3_RELEASE_READY_REPORT.md",
        "docs/PRODUCTION_DEPLOYMENT_V3_3.md",
        "docs/OPERATIONS_V3_3.md",
        "docs/PRODUCTION_PIPELINE_GUIDE_V3_3.md",
        "docs/QUALITY_INTELLIGENCE_GUIDE_V3_3.md",
        "docs/ASSET_LIFECYCLE_GUIDE_V3_3.md",
        "docs/PROJECT_INTELLIGENCE_GUIDE_V3_3.md",
        "docs/GOVERNANCE_GUIDE_V3_3.md",
        "docs/PRODUCTION_DEPLOYMENT_V3_1.md",
        "docs/OPERATIONS_V3_1.md",
        "docs/CREATIVE_COLLABORATION_GUIDE_V3_1.md",
        "docs/KNOWLEDGE_EVOLUTION_GUIDE_V3_1.md",
        "docs/ENTERPRISE_DEPLOYMENT.md",
        "docs/V2_1_RELEASE_READY_REPORT.md",
        "RELEASE_V2_2_RC1.md",
        "RELEASE_V2_2.md",
        "RELEASE_V2_3_RC1.md",
        "RELEASE_V2_3.md",
        "RELEASE_V2_4_RC1.md",
        "RELEASE_V2_4.md",
        "RELEASE_V2_5_RC1.md",
        "RELEASE_V2_5.md",
        "RELEASE_V2_6_RC1.md",
        "RELEASE_V2_6.md",
        "RELEASE_V2_7_RC1.md",
        "RELEASE_V2_7.md",
        "RELEASE_V2_1.md",
        "RELEASE_V3_RC1.md",
        "RELEASE_V3.md",
        "RELEASE_V3_1_RC1.md",
        "RELEASE_V3_1.md",
        "RELEASE_V3_2_RC1.md",
        "RELEASE_V3_2.md",
        "RELEASE_V3_3_RC1.md",
        "RELEASE_V3_3.md",
    ]
    sbom = json.loads((ROOT / "docs" / "SBOM.spdx.json").read_text(encoding="utf-8"))

    assert all((ROOT / asset).is_file() for asset in required_assets)
    assert sbom["spdxVersion"] == "SPDX-2.3"
    assert sbom["packages"][0]["versionInfo"] == manga_director.__version__


def test_v3_release_metadata_remains_historic() -> None:
    assert "v3.0.0" in (ROOT / "RELEASE_V3.md").read_text(encoding="utf-8")
    assert "v3.0.0" in (ROOT / "docs" / "V3_RELEASE_READY_REPORT.md").read_text(encoding="utf-8")


def test_v3_1_release_metadata_remains_historic_and_preserves_the_v3_0_baseline() -> None:
    roadmap = (ROOT / "docs" / "ROADMAP_v3_1.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs" / "ARCHITECTURE_V3_1.md").read_text(encoding="utf-8")
    release = (ROOT / "RELEASE_V3_1.md").read_text(encoding="utf-8")
    readiness = (ROOT / "docs" / "V3_1_RELEASE_READY_REPORT.md").read_text(encoding="utf-8")

    assert "v3.0.x development branch" in roadmap
    assert "does not change Core Architecture" in architecture
    assert "v3.1.0" in release
    assert "v3.1.0" in readiness


def test_v3_2_rc1_metadata_remains_historic() -> None:
    release = (ROOT / "RELEASE_V3_2_RC1.md").read_text(encoding="utf-8")
    readiness = (ROOT / "docs" / "V3_2_RC1_READINESS_REPORT.md").read_text(encoding="utf-8")

    assert "v3.2.0rc1" in release
    assert "v3.2.0rc1" in readiness


def test_v3_2_release_metadata_remains_historic_and_preserves_v3_1_contracts() -> None:
    roadmap = (ROOT / "docs" / "ROADMAP_v3_2.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs" / "ARCHITECTURE_V3_2.md").read_text(encoding="utf-8")
    release = (ROOT / "RELEASE_V3_2.md").read_text(encoding="utf-8")
    readiness = (ROOT / "docs" / "V3_2_RELEASE_READY_REPORT.md").read_text(encoding="utf-8")

    assert "v3.2.0" in roadmap
    assert "does not change Core" in architecture
    assert "v3.2.0" in release
    assert "v3.2.0" in readiness


def test_v3_3_rc1_metadata_remains_historic() -> None:
    release = (ROOT / "RELEASE_V3_3_RC1.md").read_text(encoding="utf-8")
    readiness = (ROOT / "docs" / "V3_3_RC1_READINESS_REPORT.md").read_text(encoding="utf-8")
    compatibility = (ROOT / "docs" / "COMPATIBILITY_V3_3_RC1.md").read_text(encoding="utf-8")

    assert "v3.3.0rc1" in release
    assert "v3.3.0rc1" in readiness
    assert "v1.x through v3.2" in compatibility


def test_v3_3_release_metadata_is_canonical_and_preserves_v3_2_contracts() -> None:
    release = (ROOT / "RELEASE_V3_3.md").read_text(encoding="utf-8")
    readiness = (ROOT / "docs" / "V3_3_RELEASE_READY_REPORT.md").read_text(encoding="utf-8")
    compatibility = (ROOT / "docs" / "COMPATIBILITY_V3_3.md").read_text(encoding="utf-8")

    assert manga_director.__version__ == "6.0.0"
    assert "v3.3.0" in release
    assert "v3.3.0" in readiness
    assert "v1.x, v2.0.x-v2.7.x" in compatibility


def test_v3_1_release_documentation_links_are_resolvable() -> None:
    documents = [
        ROOT / "README.md",
        ROOT / "RELEASE_V3_1.md",
        ROOT / "RELEASE_V3_2_RC1.md",
        ROOT / "RELEASE_V3_2.md",
        ROOT / "RELEASE_V3_3_RC1.md",
        *sorted((ROOT / "docs").glob("*V3_1.md")),
        *sorted((ROOT / "docs").glob("*V3_2*.md")),
        *sorted((ROOT / "docs").glob("*V3_3*.md")),
    ]
    for document in documents:
        contents = document.read_text(encoding="utf-8")
        for link in re.findall(r"\]\(([^)#]+)(?:#[^)]+)?\)", contents):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            assert (document.parent / link).exists(), f"{document}: broken link to {link}"
