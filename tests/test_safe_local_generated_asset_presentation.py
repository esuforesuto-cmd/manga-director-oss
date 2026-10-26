from __future__ import annotations

import hashlib
import os
import sqlite3
import stat
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
from manga_director.production.next_generation_deterministic_composite_asset_owner import (
    DeterministicCompositeAssetOwner,
)
from manga_director.production.next_generation_deterministic_page_compositor import (
    encode_rgb_png,
)
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
from manga_director.production.next_generation_page_composition import (
    AcceptedPanelSource,
    LocalPageCompositionAuthority,
    PageCompositeAsset,
    PageCompositionEvidence,
    PageCompositionRequest,
)
from manga_director.production.next_generation_page_composition_application_ledger import (
    LocalPageCompositionApplicationLedger,
    PageCompositionApplicationBinding,
)
from manga_director.production.next_generation_page_generation_plan import PanelRectangle
from manga_director.production.next_generation_page_output_proof import (
    DeterministicCompositionPageOutputProof,
    ProviderProofLookupResult,
    ResolvedPageOutput,
    build_local_page_output_proof_resolver,
    composition_evidence_sha256,
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


class _Release:
    def __init__(self) -> None:
        self.released = False

    def release(self) -> None:
        self.released = True


class _CompositionResolver:
    def __init__(self, asset_id: str, image_bytes: bytes) -> None:
        self._asset_id = asset_id
        self._image_bytes = image_bytes
        self.release = _Release()

    def resolve(
        self, project_id: str, page_id: str, output_asset_id: str
    ) -> ResolvedPageOutput:
        assert (project_id, page_id, output_asset_id) == (_PROJECT, "1", self._asset_id)
        source = AcceptedPanelSource(
            plan_id="plan-1",
            plan_fingerprint="a" * 64,
            project_id=_PROJECT,
            page_id="1",
            panel_id="panel-1",
            panel_order=1,
            request_id="request-1",
            request_fingerprint="b" * 64,
            attempt_id="panel-attempt-1",
            evidence_id="panel-evidence-1",
            asset_id="panel-asset-1",
            content_sha256="c" * 64,
            width=1,
            height=1,
            rectangle=PanelRectangle(
                left=46875, top=31250, right=953125, bottom=968750
            ),
        )
        proof = DeterministicCompositionPageOutputProof(
            project_id=_PROJECT,
            page_id="1",
            target_page_reference="target:composition:1",
            attempt_id="composition-1",
            provenance_reference="composition-provenance-1",
            asset_id=self._asset_id,
            content_sha256=hashlib.sha256(self._image_bytes).hexdigest(),
            plan_id="plan-1",
            plan_fingerprint="a" * 64,
            request_fingerprint="d" * 64,
            evidence_id="composition-evidence-1",
            evidence_sha256="e" * 64,
            ordered_sources=(source,),
        )
        return ResolvedPageOutput(proof, self._image_bytes, self.release)


class _MissingProviderProofLookup:
    def lookup(
        self, project_id: str, page_id: str, output_asset_id: str
    ) -> ProviderProofLookupResult:
        del project_id, page_id, output_asset_id
        return ProviderProofLookupResult("missing")


def _durable_composition_resolver(
    root: Path,
    *,
    output_asset_id: str,
    image_bytes: bytes,
) -> object:
    source = AcceptedPanelSource(
        plan_id="plan-1",
        plan_fingerprint="a" * 64,
        project_id=_PROJECT,
        page_id="1",
        panel_id="panel-1",
        panel_order=1,
        request_id="request-1",
        request_fingerprint="b" * 64,
        attempt_id="panel-attempt-1",
        evidence_id="panel-evidence-1",
        asset_id="panel-asset-1",
        content_sha256="c" * 64,
        width=1,
        height=1,
        rectangle=PanelRectangle(
            left=46875, top=31250, right=953125, bottom=968750
        ),
    )
    request = PageCompositionRequest(
        composition_attempt_id="composition-1",
        plan_id=source.plan_id,
        plan_fingerprint=source.plan_fingerprint,
        project_id=source.project_id,
        page_id=source.page_id,
        explicit_authorization_reference="composition-authorization-1",
        composition_provenance_reference="composition-provenance-1",
        panel_count=1,
        sources=(source,),
    )
    authority = LocalPageCompositionAuthority(root / "composition")
    assert authority.reserve(request).outcome == "created"
    asset = PageCompositeAsset(
        composition_attempt_id=request.composition_attempt_id,
        request_fingerprint=request.request_fingerprint or "",
        composition_provenance_reference=request.composition_provenance_reference,
        ordered_sources=request.sources,
        asset_id=output_asset_id,
        content_sha256=hashlib.sha256(image_bytes).hexdigest(),
    )
    owner = DeterministicCompositeAssetOwner(root / "composites")
    assert owner.register(asset, image_bytes).outcome == "registered"
    evidence = PageCompositionEvidence(
        evidence_id="composition-evidence-1",
        composition_attempt_id=request.composition_attempt_id,
        plan_id=request.plan_id,
        plan_fingerprint=request.plan_fingerprint,
        project_id=request.project_id,
        page_id=request.page_id,
        request_fingerprint=request.request_fingerprint or "",
        composition_provenance_reference=request.composition_provenance_reference,
        ordered_sources=request.sources,
        output_asset_id=asset.asset_id,
        output_sha256=asset.content_sha256,
        outcome="completed",
    )
    assert authority.commit_evidence(evidence).outcome == "updated"
    binding = PageCompositionApplicationBinding(
        application_id="composition-application-1",
        project_id=request.project_id,
        page_id=request.page_id,
        page_revision="revision-1",
        plan_id=request.plan_id,
        plan_fingerprint=request.plan_fingerprint,
        composition_attempt_id=request.composition_attempt_id,
        composition_provenance_reference=request.composition_provenance_reference,
        request_fingerprint=request.request_fingerprint or "",
        evidence_id=evidence.evidence_id,
        evidence_sha256=composition_evidence_sha256(evidence),
        composite_asset_id=asset.asset_id,
        composite_sha256=asset.content_sha256,
    )
    ledger = LocalPageCompositionApplicationLedger(root / "application")
    assert ledger.prepare(binding).outcome == "prepared"
    assert ledger.mark_applied(binding).outcome == "applied"
    return build_local_page_output_proof_resolver(
        provider_proof_lookup=_MissingProviderProofLookup(),
        composition_authority=authority,
        composite_owner=owner,
        composition_application_ledger=ledger,
    )


def test_private_composition_resolver_presents_exact_composite_bytes(tmp_path: Path) -> None:
    repository, _legacy_service, _png_bytes, binding = _seed(tmp_path)
    composite = b"exact-composite-bytes"
    resolver = _CompositionResolver(binding.output_asset_id, composite)
    service = build_generated_asset_presentation(
        repository, page_output_resolver=resolver
    )

    presentation = service.get(_PROJECT, 1)
    assert presentation.image_bytes == composite
    presentation.release()
    assert resolver.release.released


def test_concrete_durable_composition_resolver_presents_exact_bytes(
    tmp_path: Path,
) -> None:
    repository, _legacy_service, _png_bytes, _binding = _seed(tmp_path)
    output_asset_id = "composite-1"
    repository.save(
        Project(
            id=_PROJECT,
            title="V7-07",
            pages=[_page(PageState.GENERATED, output_asset_id)],
        )
    )
    composite = encode_rgb_png(2048, 3072, b"\xff" * (2048 * 3072 * 3))
    resolver = _durable_composition_resolver(
        tmp_path / "composition-sidecars",
        output_asset_id=output_asset_id,
        image_bytes=composite,
    )
    service = build_generated_asset_presentation(
        repository, page_output_resolver=resolver
    )

    presentation = service.get(_PROJECT, 1)

    assert presentation.image_bytes == composite


@pytest.mark.parametrize(
    "state",
    (PageState.GENERATED, PageState.QUALITY_CHECKED, PageState.APPROVED),
)
@pytest.mark.skipif(
    os.name != "nt",
    reason="safe exact-file presentation lease is available only on Windows",
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


@pytest.mark.skipif(os.name == "nt", reason="POSIX descriptor-relative lease contract")
def test_posix_presentation_uses_canonical_read_only_registry_bound_lease(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, service, png_bytes, binding = _seed(tmp_path)
    before = _manifest(repository._root)
    owner_root = (
        repository._next_generation_normal_execution_owner_root() / "assets"
    )
    assets_directory = owner_root / "assets"
    owner = LocalDurableAssetOwner._open_existing_for_presentation(owner_root)
    expected_owner_identity = owner._assets_root_identity
    assert expected_owner_identity.final_path == assets_directory.resolve(strict=True)

    with sqlite3.connect(f"file:{owner._registry_path.as_posix()}?mode=ro", uri=True) as connection:
        registry_binding = connection.execute(
            "SELECT attempt_id, provider_reference, media_type, digest, storage_name "
            "FROM asset_registry WHERE asset_id = ?",
            (binding.output_asset_id,),
        ).fetchone()
    assert registry_binding == (
        binding.attempt_id,
        binding.provider_reference,
        "image/png",
        hashlib.sha256(png_bytes).hexdigest(),
        next((assets_directory).glob("*.png")).name,
    )

    original_open = os.open
    original_stat = os.stat
    original_fstat = os.fstat
    owner_descriptors: list[int] = []
    asset_opens: list[tuple[str, int, int, int]] = []
    asset_stats: list[os.stat_result] = []
    asset_fstats: list[os.stat_result] = []

    def tracked_open(path: object, flags: int, *args: object, **kwargs: object) -> int:
        descriptor = original_open(path, flags, *args, **kwargs)
        if Path(path) == assets_directory:
            owner_descriptors.append(descriptor)
            assert flags & getattr(os, "O_DIRECTORY", 0)
            assert flags & getattr(os, "O_NOFOLLOW", 0)
        else:
            relative_root_descriptor = kwargs.get("dir_fd")
            if isinstance(relative_root_descriptor, int) and relative_root_descriptor in owner_descriptors:
                asset_opens.append(
                    (str(path), descriptor, relative_root_descriptor, flags)
                )
        return descriptor

    def tracked_stat(path: object, *args: object, **kwargs: object) -> os.stat_result:
        result = original_stat(path, *args, **kwargs)
        if kwargs.get("dir_fd") in owner_descriptors:
            assert kwargs.get("follow_symlinks") is False
            asset_stats.append(result)
        return result

    def tracked_fstat(descriptor: int) -> os.stat_result:
        result = original_fstat(descriptor)
        if descriptor in owner_descriptors:
            assert (result.st_dev, result.st_ino) == (
                expected_owner_identity.volume_serial,
                expected_owner_identity.file_index,
            )
        elif any(descriptor == item[1] for item in asset_opens):
            asset_fstats.append(result)
        return result

    monkeypatch.setattr(owner_module.os, "open", tracked_open)
    monkeypatch.setattr(owner_module.os, "stat", tracked_stat)
    monkeypatch.setattr(owner_module.os, "fstat", tracked_fstat)

    presentation = service.get(_PROJECT, 1)
    try:
        assert presentation.image_bytes == png_bytes
    finally:
        presentation.release()

    assert owner_descriptors
    assert len(asset_opens) == 1
    storage_name, _asset_descriptor, relative_root_descriptor, flags = asset_opens[0]
    assert storage_name == registry_binding[4]
    assert relative_root_descriptor in owner_descriptors
    assert flags & getattr(os, "O_NOFOLLOW", 0)
    assert len(asset_stats) == 2
    assert len(asset_fstats) == 2
    initial, final = asset_fstats
    assert stat.S_ISREG(initial.st_mode)
    assert 0 < initial.st_size <= owner_module._MAX_REGISTERED_BYTES
    assert (initial.st_dev, initial.st_ino) == (
        asset_stats[0].st_dev,
        asset_stats[0].st_ino,
    )
    assert (
        initial.st_dev,
        initial.st_ino,
        initial.st_mode,
        initial.st_size,
        initial.st_mtime_ns,
        initial.st_ctime_ns,
    ) == (
        final.st_dev,
        final.st_ino,
        final.st_mode,
        final.st_size,
        final.st_mtime_ns,
        final.st_ctime_ns,
    )
    assert hashlib.sha256(presentation.image_bytes).hexdigest() == registry_binding[3]
    assert _manifest(repository._root) == before


@pytest.mark.skipif(os.name == "nt", reason="POSIX final-symlink rejection contract")
def test_posix_presentation_rejects_final_symlink_without_repair(
    tmp_path: Path,
) -> None:
    repository, service, png_bytes, _binding = _seed(tmp_path)
    asset_path = next(
        (repository._next_generation_normal_execution_owner_root() / "assets" / "assets").glob("*.png")
    )
    asset_path.unlink()
    outside_path = tmp_path / "outside.png"
    outside_path.write_bytes(png_bytes)
    try:
        asset_path.symlink_to(outside_path)
    except OSError as error:
        pytest.skip(f"POSIX symlink creation unavailable: {error}")
    before = _manifest(repository._root)

    with pytest.raises(GeneratedAssetPresentationUnavailable):
        service.get(_PROJECT, 1)

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
    original_open = owner_module._open_verified_asset_lease
    monkeypatch.setattr(
        owner_module,
        "_open_verified_asset_lease",
        lambda *_args: (_ for _ in ()).throw(ValueError("unsafe identity")),
    )
    with pytest.raises(GeneratedAssetPresentationUnavailable):
        service.get(_PROJECT, 1)

    monkeypatch.setattr(owner_module, "_open_verified_asset_lease", original_open)

    class _PartialStream:
        def read(self, _size: int) -> bytes:
            return png[:-1]

        def close(self) -> None:
            pass

    partial = owner_module._AssetVerificationLease(
        _PartialStream(),
        owner_module._OpenedAssetIdentity(Path("C:/fixed.png"), 1, 1, len(png), 0),
    )
    monkeypatch.setattr(owner_module, "_open_verified_asset_lease", lambda *_args: partial)
    with pytest.raises(GeneratedAssetPresentationUnavailable):
        service.get(_PROJECT, 1)

    oversized = owner_module._AssetVerificationLease(
        _PartialStream(),
        owner_module._OpenedAssetIdentity(
            Path("C:/fixed.png"), 1, 1, 25 * 1024 * 1024 + 1, 0
        ),
    )
    monkeypatch.setattr(owner_module, "_open_verified_asset_lease", lambda *_args: oversized)
    with pytest.raises(GeneratedAssetPresentationUnavailable):
        service.get(_PROJECT, 1)
