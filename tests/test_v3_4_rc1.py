"""Release-candidate metadata and delivery-boundary contracts for v3.4."""

from __future__ import annotations

from pathlib import Path

import manga_director
from manga_director.api import ObservabilityApplication
from manga_director.api.observability import create_observability_app

ROOT = Path(__file__).resolve().parents[1]


def test_v3_4_rc1_metadata_remains_historic() -> None:
    release = (ROOT / "RELEASE_V3_4_RC1.md").read_text(encoding="utf-8")

    assert "v3.4.0rc1" in release


def test_optional_openapi_mcp_and_rc_assets_remain_available() -> None:
    application = ObservabilityApplication(
        health=lambda: None,  # type: ignore[arg-type]
        diagnostics=lambda: None,  # type: ignore[arg-type]
        repository_check=lambda: None,  # type: ignore[arg-type]
    )
    api = create_observability_app(application)
    required_assets = (
        "RELEASE_V3_4_RC1.md",
        "docs/ARCHITECTURE_SUMMARY_V3_4_RC1.md",
        "docs/COMPATIBILITY_V3_4_RC1.md",
        "docs/WORKFLOW_REGRESSION_V3_4_RC1.md",
        "docs/BENCHMARK_V3_4_RC1.md",
        "docs/SECURITY_AUDIT_V3_4_RC1.md",
        "docs/PACKAGE_AUDIT_V3_4_RC1.md",
        "docs/MIGRATION_V3_4_RC1.md",
        "docs/RELEASE_CHECKLIST_V3_4_RC1.md",
        "docs/V3_4_RC1_READINESS_REPORT.md",
    )

    assert api.version == manga_director.__version__
    assert all((ROOT / asset).is_file() for asset in required_assets)
