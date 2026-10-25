from __future__ import annotations

import hashlib
import os
import struct
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

from manga_director.api import workflow as workflow_api
from manga_director.api.workflow import LOCAL_WEB_ORIGINS, create_workflow_app
from manga_director.application.approved_asset_download import (
    ApprovedAssetDownloadService,
    ApprovedAssetDownloadUnavailable,
    build_approved_asset_download,
)
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
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
from manga_director.production.next_generation_safe_local_generated_asset_presentation import (
    SafeLocalGeneratedAssetPresentationError,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    LocalWorkflowApplicationLedgerStore,
    WorkflowApplicationLedgerBindingDTO,
    _authoritative_commit_proof,
)
from manga_director.repositories.local_file import LocalFileRepository

_PROJECT = "project-v7-09"
_ATTEMPT = "attempt:v7-09:001"
_PROVIDER = "provider:local"
_GENERATED = {
    "kind": "workflow",
    "from": "PromptBuilt",
    "to": "Generated",
    "step": "Generated",
}
_QUALITY_CHECKED = {
    "kind": "workflow",
    "from": "Generated",
    "to": "QualityChecked",
    "step": "QualityChecked",
}
_APPROVED = {
    "kind": "workflow",
    "from": "QualityChecked",
    "to": "Approved",
    "step": "Approved",
}
_BROWSER_HEADERS = {
    "Referer": f"{LOCAL_WEB_ORIGINS[0]}/projects/{_PROJECT}/pages/1",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-User": "?1",
}


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
        observed_at=datetime(2026, 10, 19, tzinfo=UTC),
        provenance_reference="provenance:v7-09:001",
        input=GenerationInputEvidenceDTO(input_reference="input:v7-09:001"),
        output=GenerationOutputEvidenceDTO(
            output_asset_id=asset_id,
            output_content_hash=_known(digest),
            media_type="image/png",
        ),
        configuration=GenerationConfigurationEvidenceDTO(
            provider_id=_known("local"),
            model_id=_known("model:v7-09"),
            model_version=_known("v1"),
            workflow_id=_known("workflow:v7-09"),
            workflow_version=_known("v1"),
            seed=_known("9"),
        ),
    )


def _approved_page(asset_id: str) -> Page:
    return Page(
        page_number=1,
        state=PageState.APPROVED,
        page_design={},
        review={},
        storyboard={},
        prompt={},
        image={"artifact_kind": "logical_output_asset", "output_asset_id": asset_id},
        quality={"passed": True},
        approval={"approved_by": "editor:local"},
        history=[_GENERATED, _QUALITY_CHECKED, _APPROVED],
    )


def _repository(tmp_path: Path, page: Page) -> LocalFileRepository:
    repository = LocalFileRepository(tmp_path / "repository")
    repository.save(Project(id=_PROJECT, title="V7-09", pages=[page]))
    return repository


def _seed(
    tmp_path: Path,
) -> tuple[LocalFileRepository, ApprovedAssetDownloadService, bytes]:
    png = _png()
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
    evidence_store = LocalGenerationEvidenceStore(normal_root / "evidence")
    assert evidence_store.persist(
        GenerationEvidenceStoreWriteRequest(
            attempt_id=_ATTEMPT,
            provider_reference=_PROVIDER,
            evidence_status="ready",
            generation_evidence=_evidence(asset_id, hashlib.sha256(png).hexdigest()),
        )
    ).outcome == "persisted"
    binding = WorkflowApplicationLedgerBindingDTO(
        attempt_id=_ATTEMPT,
        authorization_id="authorization:v7-09:001",
        project_id=_PROJECT,
        page_id="1",
        target_page_reference="target:v7-09:001",
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
    repository.save(Project(id=_PROJECT, title="V7-09", pages=[_approved_page(asset_id)]))
    return repository, build_approved_asset_download(repository), png


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


@dataclass
class _Lease:
    image_bytes: bytes = b"approved-png"
    releases: int = 0

    def release(self) -> None:
        self.releases += 1


@dataclass
class _Proof:
    _lease: _Lease

    def release(self) -> None:
        self._lease.release()


class _Presenter:
    def __init__(self, lease: _Lease, *, failure: Exception | None = None) -> None:
        self.lease = lease
        self.failure = failure
        self.calls: list[tuple[str, str, str]] = []

    def _prove(self, project_id: str, page_id: str, output_asset_id: str) -> _Proof:
        self.calls.append((project_id, page_id, output_asset_id))
        if self.failure is not None:
            raise self.failure
        return _Proof(self.lease)


def test_application_composes_approval_and_exact_proof_without_early_release(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path, _approved_page("asset:v7-09:001"))
    lease = _Lease()
    presenter = _Presenter(lease)
    service = ApprovedAssetDownloadService(repository, cast(Any, presenter))

    result = service.get(_PROJECT, 1)

    assert result.image_bytes == b"approved-png"
    assert presenter.calls == [(_PROJECT, "1", "asset:v7-09:001")]
    assert lease.releases == 0
    result.release()
    assert lease.releases == 1


def test_application_accepts_linked_artifact_without_making_evidence_an_eligibility_rule(
    tmp_path: Path,
) -> None:
    page = _approved_page("asset:v7-09:001").model_copy(
        update={
            "approval": {
                "approved_by": "editor:local",
                "review_evidence_id": "review:exact:001",
            }
        }
    )
    repository = _repository(tmp_path, page)
    presenter = _Presenter(_Lease())
    service = ApprovedAssetDownloadService(repository, cast(Any, presenter))

    result = service.get(_PROJECT, 1)

    assert result.image_bytes == b"approved-png"
    assert presenter.calls == [(_PROJECT, "1", "asset:v7-09:001")]
    result.release()


@pytest.mark.parametrize(
    ("update", "case"),
    (
        ({"state": PageState.QUALITY_CHECKED, "approval": None}, "not-approved"),
        ({"approval": {}}, "missing-approver"),
        ({"approval": {"approved_by": "editor", "role": "admin"}}, "approval-extra"),
        (
            {
                "approval": {
                    "approved_by": "editor",
                    "review_evidence_id": "../private/review",
                }
            },
            "invalid-review-reference",
        ),
        ({"history": [_GENERATED, _QUALITY_CHECKED]}, "missing-terminal-approval"),
        (
            {"history": [_GENERATED, _GENERATED, _QUALITY_CHECKED, _APPROVED]},
            "duplicate-generated",
        ),
        (
            {"history": [_GENERATED, _QUALITY_CHECKED, _APPROVED | {"extra": True}]},
            "history-extra",
        ),
        ({"image": {"path": "C:/private/image.png"}}, "path-shaped-image"),
    ),
)
def test_application_rejects_incomplete_or_ambiguous_approval_authority(
    tmp_path: Path,
    update: dict[str, object],
    case: str,
) -> None:
    page = _approved_page("asset:v7-09:001").model_copy(update=update)
    repository = _repository(tmp_path / case, page)
    presenter = _Presenter(_Lease())
    service = ApprovedAssetDownloadService(repository, cast(Any, presenter))

    with pytest.raises(ApprovedAssetDownloadUnavailable):
        service.get(_PROJECT, 1)

    assert presenter.calls == []


def test_application_redacts_proof_failure(tmp_path: Path) -> None:
    repository = _repository(tmp_path, _approved_page("asset:v7-09:001"))
    presenter = _Presenter(
        _Lease(),
        failure=SafeLocalGeneratedAssetPresentationError("C:/private/secret.png"),
    )
    service = ApprovedAssetDownloadService(repository, cast(Any, presenter))

    with pytest.raises(
        ApprovedAssetDownloadUnavailable,
        match="^approved asset download is unavailable$",
    ):
        service.get(_PROJECT, 1)


@pytest.mark.skipif(
    os.name != "nt",
    reason="safe exact-file presentation lease is available only on Windows",
)
def test_approved_page_returns_same_png_without_server_mutation(tmp_path: Path) -> None:
    repository, service, png = _seed(tmp_path)
    before = _manifest(repository._root)

    result = service.get(_PROJECT, 1)
    assert result.image_bytes == png
    result.release()

    assert _manifest(repository._root) == before


@pytest.mark.skipif(
    os.name == "nt",
    reason="POSIX exact-file lease contract",
)
def test_posix_safe_exact_file_lease_downloads_without_mutation(tmp_path: Path) -> None:
    repository, service, png_bytes = _seed(tmp_path)
    before = _manifest(repository._root)

    result = service.get(_PROJECT, 1)
    assert result.image_bytes == png_bytes
    result.release()

    assert _manifest(repository._root) == before

    unsafe_repository, unsafe_service, unsafe_png = _seed(tmp_path / "unsafe")
    asset_path = next(
        (
            unsafe_repository._next_generation_normal_execution_owner_root()
            / "assets"
            / "assets"
        ).glob("*.png")
    )
    asset_path.unlink()
    outside_path = tmp_path / "outside-download.png"
    outside_path.write_bytes(unsafe_png)
    asset_path.symlink_to(outside_path)
    unsafe_before = _manifest(unsafe_repository._root)

    with pytest.raises(ApprovedAssetDownloadUnavailable):
        unsafe_service.get(_PROJECT, 1)

    assert asset_path.is_symlink()
    assert outside_path.read_bytes() == unsafe_png
    assert _manifest(unsafe_repository._root) == unsafe_before


def test_missing_authorities_create_nothing_on_read(tmp_path: Path) -> None:
    repository = _repository(tmp_path, _approved_page("asset:missing"))
    service = build_approved_asset_download(repository)
    before = _manifest(repository._root)

    with pytest.raises(ApprovedAssetDownloadUnavailable):
        service.get(_PROJECT, 1)

    assert _manifest(repository._root) == before


class _DownloadService:
    def __init__(self, *, failure: bool = False) -> None:
        self.failure = failure
        self.calls: list[tuple[str, int]] = []
        self.releases = 0

    def get(self, project_id: str, page_number: int) -> Any:
        self.calls.append((project_id, page_number))
        if self.failure:
            raise ApprovedAssetDownloadUnavailable("C:/private/secret.png")
        return SimpleNamespace(image_bytes=_png(), release=self._release)

    def _release(self) -> None:
        self.releases += 1


def _client(
    monkeypatch: pytest.MonkeyPatch,
    service: _DownloadService | None,
) -> TestClient:
    monkeypatch.setattr(
        workflow_api,
        "approved_asset_download_for",
        lambda _application: service,
    )
    return TestClient(create_workflow_app(cast(Any, SimpleNamespace())))


def test_http_download_returns_exact_attachment_and_releases_lease(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _DownloadService()
    client = _client(monkeypatch, service)

    response = client.get(
        f"/projects/{_PROJECT}/pages/1/approved-asset-download",
        headers=_BROWSER_HEADERS,
    )

    assert response.status_code == 200 and response.content == _png()
    assert response.headers["content-type"] == "image/png"
    assert response.headers["content-disposition"] == 'attachment; filename="page-1.png"'
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert {
        "etag",
        "last-modified",
        "location",
        "content-location",
        "accept-ranges",
    }.isdisjoint(response.headers)
    assert service.calls == [(_PROJECT, 1)]
    assert service.releases == 1


@pytest.mark.parametrize("suffix", ("/", "//", "/unexpected"))
def test_http_rejects_noncanonical_download_path_without_redirect_or_service(
    monkeypatch: pytest.MonkeyPatch,
    suffix: str,
) -> None:
    service = _DownloadService()
    client = _client(monkeypatch, service)

    response = client.get(
        f"/projects/{_PROJECT}/pages/1/approved-asset-download{suffix}",
        headers=_BROWSER_HEADERS,
        follow_redirects=False,
    )

    assert response.status_code == 422
    assert response.json() == {
        "code": "invalid_input",
        "message": "Request validation failed.",
    }
    assert service.calls == []
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "location" not in response.headers
    assert "content-disposition" not in response.headers


@pytest.mark.parametrize(
    "header",
    (
        "Range",
        "If-Range",
        "If-Match",
        "If-None-Match",
        "If-Modified-Since",
        "If-Unmodified-Since",
    ),
)
def test_http_rejects_range_and_conditional_headers_before_service(
    monkeypatch: pytest.MonkeyPatch,
    header: str,
) -> None:
    service = _DownloadService()
    client = _client(monkeypatch, service)

    response = client.get(
        f"/projects/{_PROJECT}/pages/1/approved-asset-download",
        headers={**_BROWSER_HEADERS, header: "unexpected"},
    )

    assert response.status_code == 422
    assert service.calls == []
    assert response.headers["cache-control"] == "no-store"
    assert "content-disposition" not in response.headers


@pytest.mark.parametrize(
    "page_number",
    (
        "0",
        "01",
        "2147483648",
        "12345678901",
        "+1",
        "-1",
        "1.0",
        "page",
        "%31",
    ),
)
def test_http_rejects_unbounded_raw_page_number_before_service(
    monkeypatch: pytest.MonkeyPatch,
    page_number: str,
) -> None:
    service = _DownloadService()
    client = _client(monkeypatch, service)

    response = client.get(
        f"/projects/{_PROJECT}/pages/{page_number}/approved-asset-download",
        headers=_BROWSER_HEADERS,
    )

    assert response.status_code == 422
    assert service.calls == []


def test_http_accepts_maximum_bounded_page_number(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _DownloadService()
    client = _client(monkeypatch, service)

    response = client.get(
        f"/projects/{_PROJECT}/pages/2147483647/approved-asset-download",
        headers=_BROWSER_HEADERS,
    )

    assert response.status_code == 200
    assert service.calls == [(_PROJECT, 2_147_483_647)]
    assert response.headers["content-disposition"] == (
        'attachment; filename="page-2147483647.png"'
    )


@pytest.mark.parametrize(
    "headers",
    (
        {},
        {**_BROWSER_HEADERS, "Referer": "http://remote.example/page"},
        {**_BROWSER_HEADERS, "Sec-Fetch-Mode": "cors"},
        {**_BROWSER_HEADERS, "Sec-Fetch-Dest": "iframe"},
        {key: value for key, value in _BROWSER_HEADERS.items() if key != "Sec-Fetch-User"},
        {
            **_BROWSER_HEADERS,
            "Referer": "http://user@127.0.0.1:3000/projects/demo/pages/1",
        },
        {
            "Origin": LOCAL_WEB_ORIGINS[0],
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-User": "?1",
        },
    ),
)
def test_http_requires_allowed_user_activated_browser_navigation(
    monkeypatch: pytest.MonkeyPatch,
    headers: dict[str, str],
) -> None:
    service = _DownloadService()
    client = _client(monkeypatch, service)

    response = client.get(
        f"/projects/{_PROJECT}/pages/1/approved-asset-download",
        headers=headers,
    )

    assert response.status_code == 422
    assert service.calls == []


def test_http_rejects_duplicate_referer_query_and_body_before_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _DownloadService()
    client = _client(monkeypatch, service)
    route = f"/projects/{_PROJECT}/pages/1/approved-asset-download"
    duplicate_headers = [*_BROWSER_HEADERS.items(), ("Referer", _BROWSER_HEADERS["Referer"])]

    duplicate = client.get(route, headers=duplicate_headers)
    query = client.get(f"{route}?asset_id=other", headers=_BROWSER_HEADERS)
    body = client.request("GET", route, content=b'{"path":"C:/private.png"}', headers=_BROWSER_HEADERS)

    assert {duplicate.status_code, query.status_code, body.status_code} == {422}
    assert service.calls == []


def test_http_unavailable_error_is_redacted_and_has_no_download_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _DownloadService(failure=True)
    client = _client(monkeypatch, service)

    response = client.get(
        f"/projects/{_PROJECT}/pages/1/approved-asset-download",
        headers=_BROWSER_HEADERS,
    )

    assert response.status_code == 404
    assert response.json() == {"code": "not_found", "message": "Not found."}
    assert "private" not in response.text.lower()
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "content-disposition" not in response.headers
