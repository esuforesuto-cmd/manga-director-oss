"""Frozen v6.x LTS Marketplace certification descriptor contracts."""

from __future__ import annotations

from pathlib import Path

from manga_director.production import (
    MarketplaceListingDTO,
    V60CreativeProductionPlatformCoreService,
)

ROOT = Path(__file__).resolve().parents[1]


def _enum_values(field: str) -> tuple[str, ...]:
    values = MarketplaceListingDTO.model_json_schema()["properties"][field]["enum"]
    return tuple(values)


def test_lts_marketplace_certification_accepts_all_documented_local_descriptors() -> None:
    listing_types = _enum_values("listing_type")
    compatibility_labels = _enum_values("compatibility")
    listings = tuple(
        MarketplaceListingDTO(
            listing_id=f"listing:{listing_type}",
            name=listing_type,
            listing_type=listing_type,
            compatibility=compatibility_labels[index % len(compatibility_labels)],
        )
        for index, listing_type in enumerate(listing_types)
    )
    before = tuple(listing.model_dump() for listing in listings)

    report = V60CreativeProductionPlatformCoreService().marketplace_framework(listings)
    document = " ".join(
        (ROOT / "docs" / "MARKETPLACE_CERTIFICATION.md").read_text(encoding="utf-8").split()
    )

    assert listing_types == ("extension", "workflow_template", "solution_template")
    assert compatibility_labels == ("v5_additive", "v6_foundation")
    assert report.valid is True
    assert tuple(item.listing_type for item in report.listings) == tuple(sorted(listing_types))
    assert all(item.review_required is True for item in report.listings)
    assert all(item.listing_published is False for item in report.listings)
    assert all(item.package_installed is False for item in report.listings)
    assert report.marketplace_contacted is False
    assert report.marketplace_mutated is False
    assert report.planning_only is True
    assert tuple(listing.model_dump() for listing in listings) == before
    assert "`v5_additive` or `v6_foundation`" in document
    assert "does not sign a package" in document
    assert "or publish a listing" in document


def test_lts_marketplace_certification_reports_duplicate_listing_identifiers_as_invalid() -> None:
    listing = MarketplaceListingDTO(
        listing_id="listing:duplicate",
        name="Duplicate",
        listing_type="extension",
        compatibility="v5_additive",
    )

    report = V60CreativeProductionPlatformCoreService().marketplace_framework((listing, listing))

    assert report.valid is False
    assert report.duplicate_listing_ids == ("listing:duplicate",)
    assert report.marketplace_contacted is False
    assert report.marketplace_mutated is False
    assert all(item.listing_published is False for item in report.listings)
    assert all(item.package_installed is False for item in report.listings)
