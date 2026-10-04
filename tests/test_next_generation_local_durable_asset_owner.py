"""Focused local-only contracts for the durable asset owner backend."""

from __future__ import annotations

import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from manga_director.production.next_generation_asset_registration import (
    OutputAssetRegistrationService,
)
from manga_director.production.next_generation_local_durable_asset_owner import (
    LocalDurableAssetOwner,
    OwnerRegistrationMaterial,
)
from manga_director.production.next_generation_openai_output_asset_registration import (
    OpenAIAssetOwnerSinkBridge,
    OpenAIOutputAssetRegistrationAdapter,
)
from manga_director.production.next_generation_openai_provider_adapter import (
    OpenAIInMemoryGeneratedImageMaterial,
)
from manga_director.production.next_generation_provider_invocation import (
    OpaqueGeneratedOutputHandle,
    ProviderInvocationOutcome,
    ProviderInvocationReport,
)

ROOT = Path(__file__).resolve().parents[1]
_ATTEMPT = "attempt:local-owner:001"
_PROVIDER = "provider:openai"
_PNG_BYTES = b"\x89PNG\r\n\x1a\nSYNTHETIC-PRIVATE-PNG-BYTES"


class InstrumentedOwner(LocalDurableAssetOwner):
    def __init__(self, owner_root: Path, *, failure: str | None = None) -> None:
        self.events: list[str] = []
        self.failure = failure
        self.final_cleanup_attempted = False
        super().__init__(owner_root)

    def _write_staging(self, path: Path, image_bytes: bytes) -> None:
        self.events.append("stage")
        if self.failure == "stage":
            raise OSError("private staging failure")
        super()._write_staging(path, image_bytes)

    def _place_final(self, staging_path: Path, final_path: Path) -> None:
        self.events.append("final")
        if self.failure == "final":
            raise OSError("private final failure")
        super()._place_final(staging_path, final_path)

    def _commit_registration(self, *args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self.events.append("registry")
        if self.failure in {"registry", "registry_cleanup_failed"}:
            raise sqlite3.OperationalError("private registry failure")
        super()._commit_registration(*args, **kwargs)

    def _delete_private_file(self, path: Path) -> None:
        if path.parent == self._assets_directory:
            self.final_cleanup_attempted = True
        if self.failure == "registry_cleanup_failed" and path.parent == self._assets_directory:
            raise OSError("private cleanup failure")
        super()._delete_private_file(path)


def _material(
    *,
    attempt_id: str = _ATTEMPT,
    provider_reference: str = _PROVIDER,
    image_bytes: bytes = _PNG_BYTES,
    media_type: str = "image/png",
) -> OwnerRegistrationMaterial:
    return OwnerRegistrationMaterial(
        attempt_id=attempt_id,
        provider_reference=provider_reference,
        image_bytes=image_bytes,
        media_type=media_type,
    )


def _provider_outcome() -> ProviderInvocationOutcome:
    report = ProviderInvocationReport.model_construct(
        secure_execution_input_resolution_report=None,
        attempt_id=_ATTEMPT,
        provider_reference=_PROVIDER,
        findings=(),
        status="succeeded",
        succeeded=True,
        invocation_performed=True,
    )
    material = OpenAIInMemoryGeneratedImageMaterial(image_bytes=_PNG_BYTES)
    return ProviderInvocationOutcome(report, OpaqueGeneratedOutputHandle(material))


def _registered_report(owner: LocalDurableAssetOwner):
    sink = OpenAIAssetOwnerSinkBridge(owner)
    adapter = OpenAIOutputAssetRegistrationAdapter(sink)
    return OutputAssetRegistrationService().register(_ATTEMPT, _provider_outcome(), adapter)


def _registry_path(root: Path) -> Path:
    return root / "registry" / "asset-owner.sqlite3"


def test_explicit_absolute_owner_root_is_required_without_fallback(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="asset owner root is unavailable"):
        LocalDurableAssetOwner(None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="asset owner root is unavailable"):
        LocalDurableAssetOwner(Path("relative-owner-root"))
    with pytest.raises(ValueError, match="asset owner root is unavailable"):
        LocalDurableAssetOwner(tmp_path / "owner" / ".." / "escaped-owner")


def test_schema_v1_initializes_and_reopens(tmp_path: Path) -> None:
    root = tmp_path / "owner"
    first = LocalDurableAssetOwner(root)
    second = LocalDurableAssetOwner(root)

    assert (root / "registry").is_dir()
    assert (root / "staging").is_dir()
    assert (root / "assets").is_dir()
    assert first.register(_material()).outcome == "registered"
    assert second.register(_material()).outcome == "registered"


@pytest.mark.parametrize("version", (0, 2))
def test_existing_unsupported_or_newer_schema_fails_closed(tmp_path: Path, version: int) -> None:
    root = tmp_path / "owner"
    LocalDurableAssetOwner(root)
    with sqlite3.connect(_registry_path(root)) as connection:
        connection.execute(f"PRAGMA user_version = {version}")

    with pytest.raises(ValueError, match="asset owner registry is unavailable"):
        LocalDurableAssetOwner(root)


def test_malformed_existing_registry_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "owner"
    (root / "registry").mkdir(parents=True)
    _registry_path(root).write_text("not a SQLite database", encoding="utf-8")

    with pytest.raises(ValueError, match="asset owner registry is unavailable"):
        LocalDurableAssetOwner(root)


@pytest.mark.parametrize(
    "material",
    (
        _material(image_bytes=b""),
        _material(image_bytes=b"not-a-png"),
        _material(image_bytes=_PNG_BYTES + b"x" * (25 * 1024 * 1024)),
        _material(media_type="image/jpeg"),
    ),
)
def test_empty_oversized_or_invalid_media_material_fails_closed(
    tmp_path: Path, material: OwnerRegistrationMaterial
) -> None:
    result = LocalDurableAssetOwner(tmp_path / "owner").register(material)

    assert result.outcome == "failed"
    assert result.output is None
    assert result.durable_registration_confirmed is False


def test_staging_final_registry_order_and_durable_confirmation(tmp_path: Path) -> None:
    owner = InstrumentedOwner(tmp_path / "owner")
    result = owner.register(_material())

    assert owner.events == ["stage", "final", "registry"]
    assert result.outcome == "registered"
    assert result.durable_registration_confirmed is True
    assert result.output is not None
    assert result.output.output_asset_id.startswith("asset:generated:")
    assert result.output.output_content_hash is None
    assert result.output.media_type == "image/png"


def test_real_delivery_registration_commitment_is_exact_owner_bound_and_one_shot(tmp_path: Path) -> None:
    owner = LocalDurableAssetOwner(tmp_path / "owner")
    result = owner.register(_material())
    facts = owner._consume_real_delivery_registration_v1(result)

    assert facts.attempt_id == _ATTEMPT
    assert facts.provider_reference == _PROVIDER
    assert facts.digest == hashlib.sha256(_PNG_BYTES).hexdigest()
    with pytest.raises(ValueError):
        owner._consume_real_delivery_registration_v1(result)

    replay = owner.register(_material())
    with pytest.raises(ValueError):
        owner._consume_real_delivery_registration_v1(replay)


def test_identical_replay_returns_the_owner_issued_asset_and_different_attempt_is_independent(
    tmp_path: Path,
) -> None:
    owner = LocalDurableAssetOwner(tmp_path / "owner")
    first = owner.register(_material())
    replay = owner.register(_material())
    independent = owner.register(_material(attempt_id="attempt:local-owner:002"))

    assert first.output is not None
    assert replay.output is not None
    assert independent.output is not None
    assert first.output.output_asset_id == replay.output.output_asset_id
    assert first.output.output_asset_id != independent.output.output_asset_id


@pytest.mark.parametrize(
    "material",
    (
        _material(image_bytes=_PNG_BYTES + b"different"),
        _material(provider_reference="provider:other"),
    ),
)
def test_conflicting_replay_fails_closed(tmp_path: Path, material: OwnerRegistrationMaterial) -> None:
    owner = LocalDurableAssetOwner(tmp_path / "owner")
    assert owner.register(_material()).outcome == "registered"

    result = owner.register(material)

    assert result.outcome == "idempotency_conflict"
    assert result.output is None
    assert result.durable_registration_confirmed is False


def test_registry_media_conflict_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "owner"
    owner = LocalDurableAssetOwner(root)
    assert owner.register(_material()).outcome == "registered"
    with sqlite3.connect(_registry_path(root)) as connection:
        connection.execute("UPDATE asset_registry SET media_type = 'image/jpeg'")

    result = owner.register(_material())

    assert result.outcome == "idempotency_conflict"


def test_begin_immediate_serializes_concurrent_identical_replay(tmp_path: Path) -> None:
    root = tmp_path / "owner"
    first = LocalDurableAssetOwner(root)
    second = LocalDurableAssetOwner(root)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda owner: owner.register(_material()), (first, second)))

    assert {result.outcome for result in results} == {"registered"}
    assert len({result.output.output_asset_id for result in results if result.output is not None}) == 1


@pytest.mark.parametrize(
    ("failure", "expected_events", "expect_orphan"),
    (
        ("stage", ["stage"], False),
        ("final", ["stage", "final"], False),
        ("registry", ["stage", "final", "registry"], False),
        ("registry_cleanup_failed", ["stage", "final", "registry"], True),
    ),
)
def test_failures_compensate_or_remain_nonaddressable_and_redacted(
    tmp_path: Path,
    failure: str,
    expected_events: list[str],
    expect_orphan: bool,
) -> None:
    root = tmp_path / "owner"
    owner = InstrumentedOwner(root, failure=failure)
    report = _registered_report(owner)

    assert report.status == "blocked"
    assert report.registered_output is None
    assert owner.events == expected_events
    assert owner.final_cleanup_attempted is (failure in {"registry", "registry_cleanup_failed"})
    with sqlite3.connect(_registry_path(root)) as connection:
        assert connection.execute("SELECT COUNT(*) FROM asset_registry").fetchone()[0] == 0
    assert bool(tuple((root / "assets").glob("*.png"))) is expect_orphan
    serialized = report.model_dump_json()
    for private_value in (
        "SYNTHETIC-PRIVATE-PNG-BYTES",
        "private staging failure",
        "private final failure",
        "private registry failure",
        "private cleanup failure",
        "asset-owner.sqlite3",
    ):
        assert private_value not in serialized


def test_existing_missing_bytes_are_nonaddressable_and_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "owner"
    owner = LocalDurableAssetOwner(root)
    assert owner.register(_material()).outcome == "registered"
    for path in (root / "assets").glob("*.png"):
        path.unlink()

    result = owner.register(_material())

    assert result.outcome == "failed"
    assert result.output is None


def test_symlink_escape_is_rejected_when_supported(tmp_path: Path) -> None:
    root = tmp_path / "owner"
    outside = tmp_path / "outside"
    outside.mkdir()
    root.mkdir()
    try:
        (root / "assets").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable on this host")

    with pytest.raises(ValueError, match="asset owner root is unavailable"):
        LocalDurableAssetOwner(root)


def test_bridge_integrates_without_openai_types_in_the_durable_owner(tmp_path: Path) -> None:
    report = _registered_report(LocalDurableAssetOwner(tmp_path / "owner"))

    assert report.status == "registered"
    assert report.registered is True
    assert report.registered_output is not None
    assert report.registered_output.output.output_content_hash is None


def test_material_is_immutable_and_closed_failures_are_deterministic(tmp_path: Path) -> None:
    material = _material(image_bytes=b"invalid")
    with pytest.raises(FrozenInstanceError):
        material.attempt_id = "attempt:changed"  # type: ignore[misc]
    owner = LocalDurableAssetOwner(tmp_path / "owner")

    first = owner.register(material)
    second = owner.register(material)

    assert first == second


def test_source_keeps_public_surfaces_and_deferred_capabilities_out() -> None:
    source = (
        ROOT / "src/manga_director/production/next_generation_local_durable_asset_owner.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "openai",
        "GenerationEvidenceEnvelopeDTO",
        "AttemptToEvidenceBindingService",
        "AssetRetriever",
        "backup",
        "reconciliation",
        "requests.",
        "httpx.",
        "CredentialManager",
        "logging",
    ):
        assert forbidden not in source
    production_init = (ROOT / "src/manga_director/production/__init__.py").read_text(
        encoding="utf-8"
    )
    root_init = (ROOT / "src/manga_director/__init__.py").read_text(encoding="utf-8")
    assert "next_generation_local_durable_asset_owner" not in production_init
    assert "next_generation_local_durable_asset_owner" not in root_init
