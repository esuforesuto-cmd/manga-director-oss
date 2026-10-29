from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

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


def test_read_verified_at_uses_existing_owner_without_creating_state(tmp_path: Path) -> None:
    image_bytes = _png()
    root = tmp_path / "owner"
    assert DeterministicCompositeAssetOwner.read_verified_at(
        root, "composite-1"
    ).outcome == "missing"
    assert not root.exists()

    owner = DeterministicCompositeAssetOwner(root)
    owner.register(_asset(image_bytes), image_bytes)
    before = sorted(path.name for path in root.iterdir())
    observed = DeterministicCompositeAssetOwner.read_verified_at(root, "composite-1")
    after = sorted(path.name for path in root.iterdir())
    assert observed.outcome == "found"
    assert observed.asset == _asset(image_bytes)
    assert observed.image_bytes == image_bytes
    assert after == before


def test_exact_inventory_observation_is_read_only_and_verifies_asset_bytes(
    tmp_path: Path,
) -> None:
    missing_root = tmp_path / "missing"
    missing = DeterministicCompositeAssetOwner.observe_attempts_at(
        missing_root, ("composition-1",)
    )
    assert missing.outcome == "missing"
    assert missing.missing_composition_attempt_ids == ("composition-1",)
    assert not missing_root.exists()
    missing_root.mkdir()
    assert DeterministicCompositeAssetOwner.observe_attempts_at(
        missing_root, ("composition-1",)
    ).outcome == "corrupt"

    image_bytes = _png()
    root = tmp_path / "owner"
    owner = DeterministicCompositeAssetOwner(root)
    owner.register(_asset(image_bytes), image_bytes)
    assert owner.observe_attempts(("composition-1",)).outcome == "found"
    page = owner.observe_page("project-1", "page-1")
    assert page.outcome == "found"
    assert page.composition_attempt_ids == ("composition-1",)
    assert owner.observe_page("project-1", "page-other").outcome == "missing"
    partial = owner.observe_attempts(("composition-1", "composition-2"))
    assert partial.outcome == "found"
    assert partial.composition_attempt_ids == ("composition-1",)
    assert partial.missing_composition_attempt_ids == ("composition-2",)
    assert partial.assets == (_asset(image_bytes),)
    with sqlite3.connect(
        root / "deterministic-composite-assets.sqlite3"
    ) as connection:
        connection.execute(
            "CREATE TRIGGER unexpected_trigger AFTER INSERT ON composite_assets "
            "BEGIN SELECT 1; END"
        )
    assert owner.observe_page("project-1", "page-1").outcome == "corrupt"
    with sqlite3.connect(
        root / "deterministic-composite-assets.sqlite3"
    ) as connection:
        connection.execute("DROP TRIGGER unexpected_trigger")
    with sqlite3.connect(
        root / "deterministic-composite-assets.sqlite3"
    ) as connection:
        connection.execute("PRAGMA user_version = 99")
    assert owner.observe_attempts(("composition-1",)).outcome == "corrupt"


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
    assert (
        DeterministicCompositeAssetOwner.read_verified_at(root, "composite-1").outcome
        == "corrupt"
    )


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


@pytest.mark.parametrize("case", ["found", "missing", "schema", "exception"])
def test_readonly_reader_closes_retained_connection_on_all_exits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    image_bytes = _png()
    root = tmp_path / "owner"
    owner = DeterministicCompositeAssetOwner(root)
    assert owner.register(_asset(image_bytes), image_bytes).outcome == "registered"
    real_connect = sqlite3.connect
    if case == "schema":
        connection = real_connect(root / "deterministic-composite-assets.sqlite3")
        try:
            connection.execute("PRAGMA user_version = 99")
        finally:
            connection.close()

    class RetainedConnection(sqlite3.Connection):
        close_count = 0

        def close(self):
            self.close_count += 1
            super().close()

        def execute(self, *args, **kwargs):
            if case == "exception" and self.close_count == 0:
                raise sqlite3.OperationalError("injected read failure")
            return super().execute(*args, **kwargs)

    retained: list[RetainedConnection] = []

    def connect(*args, **kwargs):
        connection = real_connect(*args, **kwargs, factory=RetainedConnection)
        retained.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, "connect", connect)
    result = DeterministicCompositeAssetOwner.read_verified_at(
        root, "other-composite" if case == "missing" else "composite-1"
    )
    assert result.outcome == {
        "found": "found", "missing": "missing", "schema": "corrupt", "exception": "corrupt"
    }[case]
    assert len(retained) == 1
    assert retained[0].close_count == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        retained[0].execute("SELECT 1")
