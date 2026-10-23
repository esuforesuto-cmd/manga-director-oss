from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from manga_director.production.next_generation_deterministic_composite_asset_owner import (
    DeterministicCompositeAssetOwner,
)
from manga_director.production.next_generation_deterministic_page_compositor import encode_rgb_png
from manga_director.production.next_generation_page_composition import (
    AcceptedPanelSource,
    PageCompositeAsset,
)
from manga_director.production.next_generation_page_generation_plan import PanelRectangle


def _source() -> AcceptedPanelSource:
    return AcceptedPanelSource(
        plan_id="plan-1",
        plan_fingerprint="a" * 64,
        project_id="project-1",
        page_id="page-1",
        panel_id="panel-1",
        panel_order=1,
        request_id="request-1",
        request_fingerprint="b" * 64,
        attempt_id="attempt-1",
        evidence_id="evidence-1",
        asset_id="panel-asset-1",
        content_sha256="c" * 64,
        width=1,
        height=1,
        rectangle=PanelRectangle(left=46875, top=31250, right=953125, bottom=968750),
    )


def _asset(image_bytes: bytes, **changes: object) -> PageCompositeAsset:
    values: dict[str, object] = {
        "composition_attempt_id": "composition-1",
        "request_fingerprint": "d" * 64,
        "composition_provenance_reference": "composition-provenance-1",
        "ordered_sources": (_source(),),
        "asset_id": "composite-1",
        "content_sha256": hashlib.sha256(image_bytes).hexdigest(),
    }
    values.update(changes)
    return PageCompositeAsset(**values)


def _png() -> bytes:
    return encode_rgb_png(2048, 3072, b"\xff" * (2048 * 3072 * 3))


def test_strict_composite_registration_replay_and_readback(tmp_path: Path) -> None:
    image_bytes = _png()
    asset = _asset(image_bytes)
    owner = DeterministicCompositeAssetOwner(tmp_path / "owner")

    assert owner.register(asset, image_bytes).outcome == "registered"
    assert owner.register(asset, image_bytes).outcome == "confirmed"
    readback = owner.read_verified(asset.asset_id)
    assert readback.outcome == "found"
    assert readback.asset == asset
    assert readback.image_bytes == image_bytes


def test_same_attempt_or_asset_difference_conflicts(tmp_path: Path) -> None:
    image_bytes = _png()
    owner = DeterministicCompositeAssetOwner(tmp_path / "owner")
    assert owner.register(_asset(image_bytes), image_bytes).outcome == "registered"
    assert owner.register(
        _asset(image_bytes, request_fingerprint="e" * 64), image_bytes
    ).outcome == "conflict"
    assert owner.register(
        _asset(image_bytes, composition_attempt_id="composition-2"), image_bytes
    ).outcome == "conflict"


def test_wrong_hash_invalid_png_and_tampering_fail_closed(tmp_path: Path) -> None:
    image_bytes = _png()
    root = tmp_path / "owner"
    owner = DeterministicCompositeAssetOwner(root)
    assert owner.register(
        _asset(image_bytes, content_sha256="0" * 64), image_bytes
    ).outcome == "conflict"
    assert owner.register(_asset(image_bytes), b"not-png").outcome == "conflict"
    assert owner.register(_asset(image_bytes), image_bytes).outcome == "registered"
    with sqlite3.connect(root / "deterministic-composite-assets.sqlite3") as connection:
        storage_name = connection.execute(
            "SELECT storage_name FROM composite_assets"
        ).fetchone()[0]
    (root / "deterministic-composite-assets" / storage_name).write_bytes(b"tampered")
    assert owner.read_verified("composite-1").outcome == "corrupt"


def test_replaced_asset_directory_fails_closed_without_writing(tmp_path: Path) -> None:
    image_bytes = _png()
    root = tmp_path / "owner"
    owner = DeterministicCompositeAssetOwner(root)
    asset_directory = root / "deterministic-composite-assets"
    moved = root / "original-assets"
    asset_directory.rename(moved)
    asset_directory.write_text("not a directory", encoding="utf-8")

    assert owner.register(_asset(image_bytes), image_bytes).outcome == "failed"
    assert tuple(moved.iterdir()) == ()
