from __future__ import annotations

import hashlib
import sqlite3
import struct
import zlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from manga_director.application.generated_asset_presentation import (
    GeneratedAssetPresentationUnavailable,
    build_generated_asset_presentation,
)
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production import next_generation_local_durable_asset_owner as owner_module
from manga_director.production.next_generation_generation_evidence import (
    EvidenceValueDTO,
    GenerationConfigurationEvidenceDTO,
    GenerationEvidenceEnvelopeDTO,
    GenerationInputEvidenceDTO,
    GenerationOutputEvidenceDTO,
)
from manga_director.production.next_generation_generation_evidence_persistence import (
    GenerationEvidenceStoreWriteRequest,
    LocalGenerationEvidenceStore,
)
from manga_director.production.next_generation_local_durable_asset_owner import (
    LocalDurableAssetOwner,
    OwnerRegistrationMaterial,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    LocalWorkflowApplicationLedgerStore,
    WorkflowApplicationLedgerBindingDTO,
    _authoritative_commit_proof,
)
from manga_director.repositories.local_file import LocalFileRepository

_PROJECT = "project-v7-07"
_ATTEMPT = "attempt:v7-07:001"
_PROVIDER = "provider:local"


def _chunk(name: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + name
        + data
        + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)
    )


def _png() -> bytes:
    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00"))
        + _chunk(b"IEND", b"")
    )


def _known(value: str) -> EvidenceValueDTO:
    return EvidenceValueDTO(availability="known", value=value)


def _evidence(asset_id: str, digest: str) -> GenerationEvidenceEnvelopeDTO:
    return GenerationEvidenceEnvelopeDTO(
        attempt_id=_ATTEMPT,
        observed_at=datetime(2026, 10, 17, tzinfo=UTC),
        provenance_reference="provenance:v7-07:001",
        input=GenerationInputEvidenceDTO(input_reference="input:v7-07:001"),
        output=GenerationOutputEvidenceDTO(
            output_asset_id=asset_id,
            output_content_hash=_known(digest),
            media_type="image/png",
        ),
        configuration=GenerationConfigurationEvidenceDTO(
            provider_id=_known("local"),
            model_id=_known("model:v7-07"),
            model_version=_known("v1"),
            workflow_id=_known("workflow:v7-07"),
            workflow_version=_known("v1"),
            seed=_known("7"),
        ),
    )


def _page(state: PageState, asset_id: str) -> Page:
    return Page(
        page_number=1,
        state=state,
        page_design={},
        review={},
        storyboard={},
        prompt={},
        image={"artifact_kind": "logical_output_asset", "output_asset_id": asset_id},
        quality={} if state in {PageState.QUALITY_CHECKED, PageState.APPROVED} else None,
        approval={} if state is PageState.APPROVED else None,
    )


def _seed(
    tmp_path: Path,
    *,
    state: PageState = PageState.GENERATED,
    image_bytes: bytes | None = None,
) -> tuple[LocalFileRepository, object, bytes, WorkflowApplicationLedgerBindingDTO]:
    png = _png() if image_bytes is None else image_bytes
    repository = LocalFileRepository(tmp_path / "repository")
    normal_root = repository._next_generation_normal_execution_owner_root()
    owner = LocalDurableAssetOwner(normal_root / "assets")
    registration = owner.register(
        OwnerRegistrationMaterial(
            attempt_id=_ATTEMPT,
            provider_reference=_PROVIDER,
            image_bytes=png,
        )
    )
    assert registration.output is not None
    asset_id = registration.output.output_asset_id
    digest = hashlib.sha256(png).hexdigest()
    evidence_store = LocalGenerationEvidenceStore(normal_root / "evidence")
    assert evidence_store.persist(
        GenerationEvidenceStoreWriteRequest(
            attempt_id=_ATTEMPT,
            provider_reference=_PROVIDER,
            evidence_status="ready",
            generation_evidence=_evidence(asset_id, digest),
        )
    ).outcome == "persisted"
    binding = WorkflowApplicationLedgerBindingDTO(
        attempt_id=_ATTEMPT,
        authorization_id="authorization:v7-07:001",
        project_id=_PROJECT,
        page_id="1",
        target_page_reference="target:v7-07:001",
        provider_reference=_PROVIDER,
        output_asset_id=asset_id,
        source_state="PromptBuilt",
        target_state="Generated",
    )
    ledger = LocalWorkflowApplicationLedgerStore(
        repository._workflow_application_ledger_owner_root()
    )
    assert ledger.prepare(binding).outcome == "prepared"
    assert ledger.finalize(binding, _authoritative_commit_proof(binding)).outcome == "applied"
    repository.save(Project(id=_PROJECT, title="V7-07", pages=[_page(state, asset_id)]))
    return repository, build_generated_asset_presentation(repository), png, binding


def _manifest(root: Path) -> tuple[tuple[str, str, int, str], ...]:
    records: list[tuple[str, str, int, str]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_file():
            payload = path.read_bytes()
            records.append((relative, "file", len(payload), hashlib.sha256(payload).hexdigest()))
        else:
            records.append((relative, "directory", 0, ""))
    return tuple(records)


@pytest.mark.parametrize(
    "state",
    (PageState.GENERATED, PageState.QUALITY_CHECKED, PageState.APPROVED),
)
def test_exact_page_binding_returns_same_png_without_mutation(
    tmp_path: Path, state: PageState
) -> None:
    repository, service, png, _binding = _seed(tmp_path, state=state)
    before = _manifest(repository._root)

    presentation = service.get(_PROJECT, 1)
    assert presentation.image_bytes == png
    presentation.release()
    assert _manifest(repository._root) == before


def test_missing_sidecars_and_legacy_or_extra_artifacts_fail_without_create_on_read(
    tmp_path: Path,
) -> None:
    repository = LocalFileRepository(tmp_path / "repository")
    repository.save(
        Project(
            id=_PROJECT,
            title="V7-07",
            pages=[
                Page(
                    page_number=1,
                    state=PageState.GENERATED,
                    page_design={},
                    review={},
                    storyboard={},
                    prompt={},
                    image={"path": "C:/private/image.png"},
                )
            ],
        )
    )
    service = build_generated_asset_presentation(repository)
    before = _manifest(repository._root)

    with pytest.raises(GeneratedAssetPresentationUnavailable):
        service.get(_PROJECT, 1)
    assert _manifest(repository._root) == before

    page = repository.load(_PROJECT).page(1).model_copy(
        update={
            "image": {
                "artifact_kind": "logical_output_asset",
                "output_asset_id": "asset:missing",
                "url": "http://provider.invalid/output.png",
            }
        }
    )
    repository.save(repository.load(_PROJECT).replace_page(page))
    with pytest.raises(GeneratedAssetPresentationUnavailable):
        service.get(_PROJECT, 1)


@pytest.mark.parametrize("authority", ("ledger", "evidence", "registry"))
def test_corrupt_authority_schema_fails_closed(tmp_path: Path, authority: str) -> None:
    repository, service, _png_bytes, _binding = _seed(tmp_path)
    normal_root = repository._next_generation_normal_execution_owner_root()
    databases = {
        "ledger": repository._workflow_application_ledger_owner_root()
        / "workflow-application-ledger.sqlite3",
        "evidence": normal_root / "evidence" / "generation-evidence.sqlite3",
        "registry": normal_root / "assets" / "registry" / "asset-owner.sqlite3",
    }
    with sqlite3.connect(databases[authority]) as connection:
        connection.execute("PRAGMA user_version = 99")

    with pytest.raises(GeneratedAssetPresentationUnavailable):
        service.get(_PROJECT, 1)


@pytest.mark.parametrize("authority", ("ledger", "evidence", "registry"))
def test_wal_authority_is_rejected_before_sqlite_creates_sidecars(
    tmp_path: Path, authority: str
) -> None:
    repository, service, _png_bytes, _binding = _seed(tmp_path)
    normal_root = repository._next_generation_normal_execution_owner_root()
    database = {
        "ledger": repository._workflow_application_ledger_owner_root()
        / "workflow-application-ledger.sqlite3",
        "evidence": normal_root / "evidence" / "generation-evidence.sqlite3",
        "registry": normal_root / "assets" / "registry" / "asset-owner.sqlite3",
    }[authority]
    connection = sqlite3.connect(database)
    try:
        assert connection.execute("PRAGMA journal_mode = WAL").fetchone() == ("wal",)
    finally:
        connection.close()
    assert database.read_bytes()[18:20] == b"\x02\x02"
    assert not Path(f"{database}-wal").exists()
    assert not Path(f"{database}-shm").exists()
    before = _manifest(repository._root)

    with pytest.raises(GeneratedAssetPresentationUnavailable):
        service.get(_PROJECT, 1)

    assert _manifest(repository._root) == before


def test_ambiguous_ledger_and_cross_evidence_mismatch_fail_closed(tmp_path: Path) -> None:
    repository, service, _png_bytes, binding = _seed(tmp_path)
    ledger = LocalWorkflowApplicationLedgerStore(
        repository._workflow_application_ledger_owner_root()
    )
    duplicate = binding.model_copy(
        update={
            "attempt_id": "attempt:v7-07:duplicate",
            "authorization_id": "authorization:v7-07:duplicate",
            "output_asset_id": "asset:v7-07:duplicate",
        }
    )
    assert ledger.prepare(duplicate).outcome == "prepared"
    assert ledger.finalize(duplicate, _authoritative_commit_proof(duplicate)).outcome == "applied"
    with pytest.raises(GeneratedAssetPresentationUnavailable):
        service.get(_PROJECT, 1)

    repository, service, _png_bytes, _binding = _seed(tmp_path / "mismatch")
    evidence_database = (
        repository._next_generation_normal_execution_owner_root()
        / "evidence"
        / "generation-evidence.sqlite3"
    )
    other_provider = "provider:other"
    fingerprint = hashlib.sha256(
        "\x00".join((_ATTEMPT, other_provider, _binding.output_asset_id)).encode()
    ).hexdigest()
    with sqlite3.connect(evidence_database) as connection:
        connection.execute(
            "UPDATE generation_evidence SET provider_reference = ?, binding_fingerprint = ?",
            (other_provider, fingerprint),
        )
    with pytest.raises(GeneratedAssetPresentationUnavailable):
        service.get(_PROJECT, 1)


def test_missing_registry_digest_tamper_and_strict_png_trailing_data_fail_closed(
    tmp_path: Path,
) -> None:
    repository, service, _png_bytes, _binding = _seed(tmp_path / "missing")
    registry = (
        repository._next_generation_normal_execution_owner_root()
        / "assets"
        / "registry"
        / "asset-owner.sqlite3"
    )
    with sqlite3.connect(registry) as connection:
        connection.execute("DELETE FROM asset_registry")
    with pytest.raises(GeneratedAssetPresentationUnavailable):
        service.get(_PROJECT, 1)

    repository, service, _png_bytes, _binding = _seed(tmp_path / "digest")
    asset = next(
        (
            repository._next_generation_normal_execution_owner_root()
            / "assets"
            / "assets"
        ).glob("*.png")
    )
    asset.write_bytes(_png() + b"changed")
    with pytest.raises(GeneratedAssetPresentationUnavailable):
        service.get(_PROJECT, 1)

    repository, service, _png_bytes, _binding = _seed(
        tmp_path / "trailing", image_bytes=_png() + b"trailing"
    )
    with pytest.raises(GeneratedAssetPresentationUnavailable):
        service.get(_PROJECT, 1)


def test_unsafe_reparse_identity_oversize_and_partial_read_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, service, png, _binding = _seed(tmp_path)
    original_reparse = owner_module._is_link_or_reparse_point
    monkeypatch.setattr(
        owner_module,
        "_is_link_or_reparse_point",
        lambda path: path.suffix == ".png" or original_reparse(path),
    )
    with pytest.raises(GeneratedAssetPresentationUnavailable):
        service.get(_PROJECT, 1)

    monkeypatch.setattr(owner_module, "_is_link_or_reparse_point", original_reparse)
    original_open = owner_module._open_verified_windows_lease
    monkeypatch.setattr(
        owner_module,
        "_open_verified_windows_lease",
        lambda *_args: (_ for _ in ()).throw(ValueError("unsafe identity")),
    )
    with pytest.raises(GeneratedAssetPresentationUnavailable):
        service.get(_PROJECT, 1)

    monkeypatch.setattr(owner_module, "_open_verified_windows_lease", original_open)

    class _PartialStream:
        def read(self, _size: int) -> bytes:
            return png[:-1]

        def close(self) -> None:
            pass

    partial = owner_module._AssetVerificationLease(
        _PartialStream(),
        owner_module._OpenedAssetIdentity(Path("C:/fixed.png"), 1, 1, len(png), 0),
    )
    monkeypatch.setattr(owner_module, "_open_verified_windows_lease", lambda *_args: partial)
    with pytest.raises(GeneratedAssetPresentationUnavailable):
        service.get(_PROJECT, 1)

    oversized = owner_module._AssetVerificationLease(
        _PartialStream(),
        owner_module._OpenedAssetIdentity(
            Path("C:/fixed.png"), 1, 1, 25 * 1024 * 1024 + 1, 0
        ),
    )
    monkeypatch.setattr(owner_module, "_open_verified_windows_lease", lambda *_args: oversized)
    with pytest.raises(GeneratedAssetPresentationUnavailable):
        service.get(_PROJECT, 1)
