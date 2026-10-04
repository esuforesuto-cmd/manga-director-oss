"""Stable-release metadata and transport boundary contracts for v3.3."""

from __future__ import annotations

import json
from pathlib import Path

import manga_director
from manga_director.api import ObservabilityApplication
from manga_director.api.observability import create_observability_app

ROOT = Path(__file__).resolve().parents[1]


def test_v3_3_release_metadata_uses_one_canonical_python_version() -> None:
    sbom = json.loads((ROOT / "docs/SBOM.spdx.json").read_text(encoding="utf-8"))
    frontend = json.loads((ROOT / "web/package.json").read_text(encoding="utf-8"))
    release = (ROOT / "RELEASE_V3_3.md").read_text(encoding="utf-8")

    assert manga_director.__version__ == "6.0.0"
    assert sbom["packages"][0]["versionInfo"] == manga_director.__version__
    assert frontend["version"] == manga_director.__version__.replace("rc", "-rc.")
    assert "v3.3.0" in release


def test_optional_openapi_and_stable_release_assets_use_the_canonical_version() -> None:
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
    )
    api = create_observability_app(application)
    required_assets = (
        "RELEASE_V3_3.md",
        "docs/ARCHITECTURE_SUMMARY_V3_3.md",
        "docs/COMPATIBILITY_V3_3.md",
        "docs/WORKFLOW_REGRESSION_V3_3.md",
        "docs/BENCHMARK_V3_3.md",
        "docs/SECURITY_AUDIT_V3_3.md",
        "docs/PACKAGE_AUDIT_V3_3.md",
        "docs/MIGRATION_V3_3.md",
        "docs/RELEASE_CHECKLIST_V3_3.md",
        "docs/V3_3_RELEASE_READY_REPORT.md",
    )

    assert api.version == manga_director.__version__
    assert all((ROOT / asset).is_file() for asset in required_assets)
