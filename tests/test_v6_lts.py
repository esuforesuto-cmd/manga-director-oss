"""Maintenance contracts for the v6.x Creative Production Platform LTS line."""

from __future__ import annotations

from pathlib import Path

import manga_director
from benchmarks.v6_0_platform_rc1 import run as run_platform_kernel_benchmark
from manga_director.domain.state_machine import PageState
from manga_director.production import (
    ExtensionFrameworkDTO,
    MarketplaceListingDTO,
    SDKCapabilityDTO,
    V60CreativeProductionPlatformCoreService,
)
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "lts-page-1"},
        state=PageState.QUALITY_CHECKED,
        artifacts={
            PageState.STORYBOARDED.value: {"panels": []},
            PageState.QUALITY_CHECKED.value: {"status": "passed"},
        },
        metadata={
            "story_context": {},
            "character_context": {},
            "world_context": {},
            "timeline_context": {},
        },
    )


def test_lts_stability_repeats_one_page_platform_health_projection() -> None:
    context = _context()
    before = context.model_dump()
    service = V60CreativeProductionPlatformCoreService()

    reports = tuple(service.platform_core("lts-project", context) for _ in range(25))

    assert manga_director.__version__ == "6.0.0"
    assert all(report.kernel.kernel.page_reference == "lts-page-1" for report in reports)
    assert all(report.automatic_action_taken is False for report in reports)
    assert context.model_dump() == before


def test_lts_platform_kernel_benchmark_preserves_the_one_page_context() -> None:
    context = _context()
    before = context.model_dump()

    elapsed = run_platform_kernel_benchmark(iterations=1, context=context)

    assert elapsed >= 0.0
    assert context.page == {"id": "lts-page-1"}
    assert context.model_dump() == before
def test_lts_sdk_extension_and_marketplace_compatibility_remain_advisory() -> None:
    service = V60CreativeProductionPlatformCoreService()
    sdk = service.sdk_foundation(
        tuple(
            SDKCapabilityDTO(
                capability_id=f"sdk:{surface}",
                surface=surface,
                source_reference="manga_director",
                compatibility="v6_foundation",
            )
            for surface in ("python", "cli", "fastapi", "mcp", "web_ui")
        )
    )
    extensions = service.extension_framework(
        (
            ExtensionFrameworkDTO(
                extension_id="extension:analytics",
                name="Analytics",
                extension_type="analytics",
                compatibility="v6_foundation",
            ),
        )
    )
    marketplace = service.marketplace_framework(
        (
            MarketplaceListingDTO(
                listing_id="listing:analytics",
                name="Analytics",
                listing_type="extension",
                compatibility="v6_foundation",
            ),
        )
    )

    assert sdk.compatible is True
    assert sdk.surface_count == 5
    assert sdk.sdk_published is False
    assert extensions.compatible is True
    assert extensions.extensions[0].extension_loaded is False
    assert marketplace.valid is True
    assert marketplace.marketplace_contacted is False
    assert marketplace.listings[0].listing_published is False


def test_lts_maintenance_documents_are_available() -> None:
    documents = (
        "docs/V6_LTS_PLAN.md",
        "docs/V6_LTS_POLICY.md",
        "docs/PLATFORM_HEALTH_REPORT.md",
        "docs/SDK_COMPATIBILITY_MATRIX.md",
        "docs/EXTENSION_COMPATIBILITY_MATRIX.md",
        "docs/MARKETPLACE_CERTIFICATION.md",
        "docs/SECURITY_MAINTENANCE.md",
        "docs/TECHNICAL_DEBT_REGISTER.md",
    )

    assert all((ROOT / document).is_file() for document in documents)
    supported_versions = (ROOT / "SUPPORTED_VERSIONS.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "`6.0.x` | LTS current line" in supported_versions
    assert "docs/V6_LTS_POLICY.md" in readme
