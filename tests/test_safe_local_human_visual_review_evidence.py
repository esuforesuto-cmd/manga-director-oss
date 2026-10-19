from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import struct
import zlib
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi.testclient import TestClient

from manga_director.api import workflow as workflow_api
from manga_director.api.workflow import create_workflow_app
from manga_director.application import human_visual_review_evidence as application_module
from manga_director.application.human_visual_review_evidence import (
    HumanVisualReviewEvidencePersistenceUnavailable,
    HumanVisualReviewEvidenceService,
    HumanVisualReviewEvidenceUnavailable,
    build_human_visual_review_evidence,
)
from manga_director.application.human_visual_review_readiness import (
    ReviewChecklistDecision,
    _HumanVisualReviewReadinessProof,
    _HumanVisualReviewSubmission,
    build_human_visual_review_readiness,
)
from manga_director.application.workflow import WorkflowApplicationService
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production.next_generation_durable_human_visual_review_evidence import (
    DurableHumanVisualReviewEvidenceUnavailable,
    _EvidenceChecklistItem,
    _HumanVisualReviewEvidencePayload,
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
from manga_director.production.next_generation_workflow_application_ledger import (
    LocalWorkflowApplicationLedgerStore,
    WorkflowApplicationLedgerBindingDTO,
    _authoritative_commit_proof,
)
from manga_director.production.reliability import WorkflowConsistencyReport
from manga_director.repositories.local_file import LocalFileRepository

_PROJECT = "project-v7-10"
_ATTEMPT = "attempt:v7-10:001"
_PROVIDER = "provider:local"
_CRITERIA = (
    "character_identity",
    "face",
    "costume",
    "props",
    "pose",
    "gaze",
    "emotion",
    "screen_direction",
    "location",
    "time",
    "composition",
    "panel_intent",
    "visible_corruption",
    "truncation",
    "watermark",
    "unsafe_content",
    "unintended_text",
    "continuity_comparison",
)


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
        provenance_reference="provenance:v7-10:001",
        input=GenerationInputEvidenceDTO(input_reference="input:v7-10:001"),
        output=GenerationOutputEvidenceDTO(
            output_asset_id=asset_id,
            output_content_hash=_known(digest),
            media_type="image/png",
        ),
        configuration=GenerationConfigurationEvidenceDTO(
            provider_id=_known("local"),
            model_id=_known("model:v7-10"),
            model_version=_known("v1"),
            workflow_id=_known("workflow:v7-10"),
            workflow_version=_known("v1"),
            seed=_known("10"),
        ),
    )


def _page(state: PageState, asset_id: str) -> Page:
    history = [
        {
            "kind": "workflow",
            "from": "PromptBuilt",
            "to": "Generated",
            "step": "generate",
        }
    ]
    if state in {PageState.QUALITY_CHECKED, PageState.APPROVED}:
        history.append(
            {
                "kind": "workflow",
                "from": "Generated",
                "to": "QualityChecked",
                "step": "quality",
            }
        )
    if state is PageState.APPROVED:
        history.append(
            {
                "kind": "workflow",
                "from": "QualityChecked",
                "to": "Approved",
                "step": "approve",
            }
        )
    panel = {
        "page_id": "1",
        "props": ["prop:book"],
        "location": "location:studio",
        "time": "time:day",
    }
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
        metadata={
            "previous_page": {**panel, "panel_id": "panel:before"},
            "current_page": {**panel, "panel_id": "panel:current"},
        },
        history=history,
    )


def _seed(
    tmp_path: Path,
    *,
    state: PageState = PageState.QUALITY_CHECKED,
) -> tuple[LocalFileRepository, HumanVisualReviewEvidenceService]:
    png = _png()
    repository = LocalFileRepository(tmp_path / "repository")
    normal_root = repository._next_generation_normal_execution_owner_root()
    registration = LocalDurableAssetOwner(normal_root / "assets").register(
        OwnerRegistrationMaterial(
            attempt_id=_ATTEMPT,
            provider_reference=_PROVIDER,
            image_bytes=png,
        )
    )
    assert registration.output is not None
    asset_id = registration.output.output_asset_id
    assert LocalGenerationEvidenceStore(normal_root / "evidence").persist(
        GenerationEvidenceStoreWriteRequest(
            attempt_id=_ATTEMPT,
            provider_reference=_PROVIDER,
            evidence_status="ready",
            generation_evidence=_evidence(asset_id, hashlib.sha256(png).hexdigest()),
        )
    ).outcome == "persisted"
    binding = WorkflowApplicationLedgerBindingDTO(
        attempt_id=_ATTEMPT,
        authorization_id="authorization:v7-10:001",
        project_id=_PROJECT,
        page_id="1",
        target_page_reference="target:v7-10:001",
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
    repository.save(Project(id=_PROJECT, title="V7-10", pages=[_page(state, asset_id)]))
    readiness = build_human_visual_review_readiness(repository)
    return repository, build_human_visual_review_evidence(repository, readiness)


def _checklist(*, blocked: str | None = None) -> tuple[ReviewChecklistDecision, ...]:
    return tuple(
        ReviewChecklistDecision(
            criterion=criterion,
            outcome="blocked" if criterion == blocked else "acceptable",
            rationale="Reviewed directly",
        )
        for criterion in _CRITERIA
    )


def _submission(
    *,
    blocked: str | None = None,
    reviewed_at: datetime | None = None,
) -> dict[str, object]:
    return {
        "reviewer_id": "reviewer:local",
        "reviewed_at": reviewed_at or datetime(2026, 10, 19, 12, 0, tzinfo=UTC),
        "checklist": _checklist(blocked=blocked),
        "overall_judgment": (
            "blocked" if blocked else "acceptable_for_approval_consideration"
        ),
        "rationale": "Complete local visual review",
    }


def _body() -> dict[str, object]:
    return {
        "reviewerId": "reviewer:local",
        "reviewedAt": "2026-10-19T12:00:00Z",
        "checklist": [
            {
                "criterion": criterion,
                "outcome": "acceptable",
                "rationale": "Reviewed directly",
            }
            for criterion in sorted(_CRITERIA)
        ],
        "overallJudgment": "acceptable_for_approval_consideration",
        "rationale": "Complete local visual review",
    }


def _review_database(repository: LocalFileRepository) -> Path:
    return (
        repository._next_generation_normal_execution_owner_root()
        / "review-evidence"
        / "human-visual-review-evidence.sqlite3"
    )


def _manifest(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


@pytest.mark.skipif(
    os.name != "nt",
    reason="safe exact-file presentation lease is available only on Windows",
)
@pytest.mark.parametrize(
    ("state", "blocked", "status", "ready"),
    (
        (PageState.GENERATED, None, "needs_review", False),
        (PageState.QUALITY_CHECKED, None, "ready", True),
        (PageState.QUALITY_CHECKED, "face", "blocked", False),
    ),
)
def test_records_exact_server_resolved_report_and_preserves_project(
    tmp_path: Path,
    state: PageState,
    blocked: str | None,
    status: str,
    ready: bool,
) -> None:
    repository, service = _seed(tmp_path, state=state)
    before_project = repository.load(_PROJECT)
    before_manifest = _manifest(repository._root)

    result = service.record(_PROJECT, 1, **_submission(blocked=blocked))

    assert result.status == status
    assert result.ready is ready
    assert result.page_state == state.value
    assert result.evidence_recorded is True
    assert result.idempotent_replay is False
    assert result.analysis_only is True
    assert repository.load(_PROJECT) == before_project
    after_manifest = _manifest(repository._root)
    assert {
        path: content
        for path, content in after_manifest.items()
        if "/review-evidence/" not in f"/{path}"
    } == before_manifest
    with sqlite3.connect(_review_database(repository)) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM human_visual_review_evidence_records"
        ).fetchone() == (1,)


@pytest.mark.skipif(
    os.name != "nt",
    reason="safe exact-file presentation lease is available only on Windows",
)
def test_exact_retry_confirms_and_distinct_review_appends(tmp_path: Path) -> None:
    repository, service = _seed(tmp_path)

    first = service.record(_PROJECT, 1, **_submission())
    replay = service.record(_PROJECT, 1, **_submission())
    later = service.record(
        _PROJECT,
        1,
        **_submission(reviewed_at=datetime(2026, 10, 19, 12, 1, tzinfo=UTC)),
    )

    assert first.idempotent_replay is False
    assert replay.idempotent_replay is True
    assert later.idempotent_replay is False
    with sqlite3.connect(_review_database(repository)) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM human_visual_review_evidence_records"
        ).fetchone() == (2,)


@pytest.mark.skipif(
    os.name == "nt",
    reason="non-Windows fail-closed behavior is not applicable on Windows",
)
def test_unsupported_exact_file_lease_creates_no_review_sidecar(tmp_path: Path) -> None:
    repository, service = _seed(tmp_path)

    with pytest.raises(HumanVisualReviewEvidenceUnavailable):
        service.record(_PROJECT, 1, **_submission())

    assert not _review_database(repository).parent.exists()


@pytest.mark.skipif(
    os.name != "nt",
    reason="safe exact-file presentation lease is available only on Windows",
)
def test_approved_or_corrupt_authority_creates_no_review_row(tmp_path: Path) -> None:
    approved_repository, approved = _seed(tmp_path / "approved", state=PageState.APPROVED)
    with pytest.raises(HumanVisualReviewEvidenceUnavailable):
        approved.record(_PROJECT, 1, **_submission())
    assert not _review_database(approved_repository).parent.exists()

    repository, service = _seed(tmp_path / "corrupt")
    evidence_database = (
        repository._next_generation_normal_execution_owner_root()
        / "evidence"
        / "generation-evidence.sqlite3"
    )
    with sqlite3.connect(evidence_database) as connection:
        connection.execute("PRAGMA user_version=99")
    with pytest.raises(HumanVisualReviewEvidenceUnavailable):
        service.record(_PROJECT, 1, **_submission())
    assert not _review_database(repository).parent.exists()


@pytest.mark.skipif(
    os.name != "nt",
    reason="safe exact-file presentation lease is available only on Windows",
)
@pytest.mark.parametrize(
    "state",
    (
        PageState.DRAFT,
        PageState.DESIGNED,
        PageState.REVIEWED,
        PageState.STORYBOARDED,
        PageState.PROMPT_BUILT,
        PageState.APPROVED,
    ),
)
def test_non_assessable_states_create_no_review_sidecar(
    tmp_path: Path,
    state: PageState,
) -> None:
    repository, service = _seed(tmp_path, state=state)
    before = _manifest(repository._root)

    with pytest.raises(HumanVisualReviewEvidenceUnavailable):
        service.record(_PROJECT, 1, **_submission())

    assert _manifest(repository._root) == before
    assert not _review_database(repository).parent.exists()


@pytest.mark.skipif(
    os.name != "nt",
    reason="safe exact-file presentation lease is available only on Windows",
)
def test_qa_derived_block_is_recorded_without_approval_or_page_mutation(
    tmp_path: Path,
) -> None:
    repository, service = _seed(tmp_path)
    project = repository.load(_PROJECT)
    page = project.page(1)
    previous = dict(cast(dict[str, object], page.metadata["previous_page"]))
    current = dict(cast(dict[str, object], page.metadata["current_page"]))
    previous["panel_id"] = "panel:shared"
    current["panel_id"] = "panel:shared"
    current["location"] = "location:other"
    repository.save(
        project.replace_page(
            page.model_copy(
                update={
                    "metadata": page.metadata
                    | {"previous_page": previous, "current_page": current}
                }
            )
        )
    )
    before_project = repository.load(_PROJECT)

    result = service.record(_PROJECT, 1, **_submission())

    assert result.status == "blocked"
    assert result.ready is False
    assert "VISUAL_QA_BLOCKED" in {finding.code for finding in result.findings}
    assert repository.load(_PROJECT) == before_project
    assert repository.load(_PROJECT).page(1).approval is None


@pytest.mark.skipif(
    os.name != "nt",
    reason="safe exact-file presentation lease is available only on Windows",
)
def test_transient_assessment_and_reads_create_no_review_record(tmp_path: Path) -> None:
    repository, _service = _seed(tmp_path)
    readiness = build_human_visual_review_readiness(repository)
    before = _manifest(repository._root)

    assert readiness.assess(_PROJECT, 1, **_submission()).status == "ready"
    assert repository.load(_PROJECT).page(1).state is PageState.QUALITY_CHECKED

    assert _manifest(repository._root) == before
    assert not _review_database(repository).parent.exists()


@pytest.mark.skipif(
    os.name != "nt",
    reason="safe exact-file presentation lease is available only on Windows",
)
@pytest.mark.parametrize(
    "corruption",
    ("missing_history", "state_mismatch", "duplicate_generated"),
)
def test_workflow_history_corruption_creates_no_review_record(
    tmp_path: Path,
    corruption: str,
) -> None:
    repository, service = _seed(tmp_path)
    project = repository.load(_PROJECT)
    page = project.page(1)
    generated = {
        "kind": "workflow",
        "from": "PromptBuilt",
        "to": "Generated",
        "step": "generate",
    }
    if corruption == "missing_history":
        history: list[dict[str, str]] = []
    elif corruption == "state_mismatch":
        history = [generated]
    else:
        history = [generated, generated, *cast(list[dict[str, str]], page.history[1:])]
    repository.save(project.replace_page(page.model_copy(update={"history": history})))
    before = _manifest(repository._root)

    with pytest.raises(HumanVisualReviewEvidenceUnavailable):
        service.record(_PROJECT, 1, **_submission())

    assert _manifest(repository._root) == before
    assert not _review_database(repository).parent.exists()


def test_application_owns_lease_through_persistence_and_releases_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    released = 0
    persisted_while_held = False
    report = SimpleNamespace(
        status="ready",
        ready=True,
        persisted_page_state=PageState.QUALITY_CHECKED,
        findings=(),
        missing_prerequisites=(),
    )

    class Proof:
        def __init__(self) -> None:
            self.report = report
            self._workflow_consistency = SimpleNamespace(valid=True)

        def release(self) -> None:
            nonlocal released
            released += 1

    proof = Proof()
    readiness = SimpleNamespace(_prove=lambda *_args, **_kwargs: proof)

    class Owner:
        def persist(self, _payload: object) -> SimpleNamespace:
            nonlocal persisted_while_held
            persisted_while_held = released == 0
            return SimpleNamespace(outcome="recorded")

    payload = _HumanVisualReviewEvidencePayload(
        review_id="review:v7-10:lease",
        project_id=_PROJECT,
        page_id="1",
        page_number=1,
        page_state="QualityChecked",
        attempt_id=_ATTEMPT,
        output_asset_id="asset:v7-10:001",
        provenance_reference="provenance:v7-10:001",
        qa_report_reference="qa-report:v7-10:001",
        reviewer_id="reviewer:local",
        reviewed_at=datetime(2026, 10, 19, tzinfo=UTC),
        checklist=tuple(
            _EvidenceChecklistItem(
                criterion=criterion,
                outcome="acceptable",
                rationale="Reviewed directly",
            )
            for criterion in sorted(_CRITERIA)
        ),
        overall_judgment="acceptable_for_approval_consideration",
        rationale="Complete local visual review",
        status="ready",
        ready=True,
        findings=(),
        missing_prerequisites=(),
    )
    monkeypatch.setattr(application_module, "_payload", lambda _report: payload)
    service = HumanVisualReviewEvidenceService(cast(object, readiness), cast(object, Owner()))

    result = service.record(_PROJECT, 1, **_submission())

    assert result.evidence_recorded is True
    assert persisted_while_held is True
    assert released == 1


def test_application_releases_once_when_persistence_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    released = 0
    proof = SimpleNamespace(
        report=SimpleNamespace(),
        _workflow_consistency=SimpleNamespace(valid=True),
        release=lambda: None,
    )

    def release() -> None:
        nonlocal released
        released += 1

    proof.release = release
    readiness = SimpleNamespace(_prove=lambda *_args, **_kwargs: proof)

    class Owner:
        def persist(self, _payload: object) -> None:
            raise DurableHumanVisualReviewEvidenceUnavailable("redacted")

    monkeypatch.setattr(application_module, "_payload", lambda _report: object())
    service = HumanVisualReviewEvidenceService(cast(object, readiness), cast(object, Owner()))

    with pytest.raises(HumanVisualReviewEvidencePersistenceUnavailable):
        service.record(_PROJECT, 1, **_submission())
    assert released == 1


def test_private_submission_and_proof_repr_are_redacted() -> None:
    submission = _HumanVisualReviewSubmission(**_submission())
    proof = _HumanVisualReviewReadinessProof(
        report=cast(object, SimpleNamespace(secret="human rationale")),
        _asset_proof=cast(object, SimpleNamespace(release=lambda: None)),
        _workflow_consistency=WorkflowConsistencyReport(
            project_id=_PROJECT,
            page_number=1,
            valid=True,
            current_state=PageState.QUALITY_CHECKED,
            errors=[],
        ),
    )

    assert repr(submission) == "_HumanVisualReviewSubmission(<redacted>)"
    assert repr(proof) == "_HumanVisualReviewReadinessProof(<redacted>)"
    assert "reviewer:local" not in repr(submission)
    assert "human rationale" not in repr(proof)


def test_http_route_accepts_only_explicit_allowed_origin_and_redacts_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, int, dict[str, object]]] = []

    def record(project_id: str, page_number: int, **values: object) -> SimpleNamespace:
        calls.append((project_id, page_number, values))
        return SimpleNamespace(
            status="ready",
            ready=True,
            page_state="QualityChecked",
            findings=(),
            missing_prerequisites=(),
            idempotent_replay=False,
        )

    monkeypatch.setattr(
        workflow_api,
        "human_visual_review_evidence_for",
        lambda _application: SimpleNamespace(record=record),
    )
    client = TestClient(create_workflow_app(cast(WorkflowApplicationService, object())))
    headers = {"Origin": "http://127.0.0.1:3000"}

    response = client.post(
        "/projects/demo/pages/1/visual-review-evidence",
        json=_body(),
        headers=headers,
    )
    query = client.post(
        "/projects/demo/pages/1/visual-review-evidence?assetId=other",
        json=_body(),
        headers=headers,
    )
    selector = client.post(
        "/projects/demo/pages/1/visual-review-evidence",
        json=_body() | {"reviewId": "review:caller"},
        headers=headers,
    )
    missing_origin = client.post(
        "/projects/demo/pages/1/visual-review-evidence",
        json=_body(),
    )
    bad_page = client.post(
        "/projects/demo/pages/01/visual-review-evidence",
        json=_body(),
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "ready": True,
        "pageState": "QualityChecked",
        "findings": [],
        "missingPrerequisites": [],
        "analysisOnly": True,
        "evidenceRecorded": True,
        "idempotentReplay": False,
    }
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert {"etag", "last-modified", "location", "content-disposition"}.isdisjoint(
        response.headers
    )
    assert {query.status_code, selector.status_code, missing_origin.status_code, bad_page.status_code} == {422}
    assert len(calls) == 1
    assert calls[0][0:2] == ("demo", 1)
    assert not any(
        part in response.text.lower()
        for part in ("reviewer", "attempt", "asset", "provider", "digest", "path", "sqlite")
    )


def test_http_route_rejects_duplicate_origin_and_redacts_persistence_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def record(*_args: object, **_kwargs: object) -> None:
        nonlocal calls
        calls += 1
        raise HumanVisualReviewEvidencePersistenceUnavailable("private database path")

    monkeypatch.setattr(
        workflow_api,
        "human_visual_review_evidence_for",
        lambda _application: SimpleNamespace(record=record),
    )
    client = TestClient(create_workflow_app(cast(WorkflowApplicationService, object())))
    duplicate = client.post(
        "/projects/demo/pages/1/visual-review-evidence",
        json=_body(),
        headers=[
            ("Origin", "http://127.0.0.1:3000"),
            ("Origin", "http://localhost:3000"),
        ],
    )
    unavailable = client.post(
        "/projects/demo/pages/1/visual-review-evidence",
        json=_body(),
        headers={"Origin": "http://127.0.0.1:3000"},
    )

    assert duplicate.status_code == 422
    assert unavailable.status_code == 503
    assert unavailable.json() == {
        "code": "persistence_unavailable",
        "message": "Persistence unavailable.",
    }
    assert "private" not in unavailable.text
    assert unavailable.headers["cache-control"] == "no-store"
    assert calls == 1


def test_http_route_rejects_nonlocal_or_unbounded_requests_before_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def record(*_args: object, **_kwargs: object) -> None:
        nonlocal calls
        calls += 1

    monkeypatch.setattr(
        workflow_api,
        "human_visual_review_evidence_for",
        lambda _application: SimpleNamespace(record=record),
    )
    client = TestClient(create_workflow_app(cast(WorkflowApplicationService, object())))
    route = "/projects/demo/pages/1/visual-review-evidence"
    allowed = {"Origin": "http://127.0.0.1:3000"}
    selectors = (
        {"projectId": "other"},
        {"pageNumber": 2},
        {"pageId": "2"},
        {"reviewId": "review:caller"},
        {"assetId": "asset:caller"},
        {"attemptId": "attempt:caller"},
        {"provider": "remote"},
        {"digest": "0" * 64},
        {"path": "C:/private/image.png"},
        {"storageName": "private.png"},
        {"root": "C:/private"},
        {"url": "https://remote.invalid/image.png"},
        {"status": "ready"},
        {"ready": True},
        {"token": "secret-value"},
    )
    incomplete = _body()
    incomplete["checklist"] = cast(list[object], incomplete["checklist"])[:-1]
    duplicate = _body()
    duplicate_items = cast(list[dict[str, object]], duplicate["checklist"])
    duplicate_items[-1] = dict(duplicate_items[0])
    invalid_not_applicable = _body()
    cast(list[dict[str, object]], invalid_not_applicable["checklist"])[0]["outcome"] = (
        "not_applicable"
    )
    responses = (
        client.post(route, json=_body(), headers={"Origin": "null"}),
        client.post(route, json=_body(), headers={"Origin": "http://192.168.1.2:3000"}),
        client.post(route, json=_body(), headers={"Origin": "http://[::1"}),
        client.post(
            route,
            content=json.dumps(_body(), default=str),
            headers=allowed | {"Content-Type": "text/plain"},
        ),
        client.post(
            route,
            json=_body(),
            headers=allowed | {"Transfer-Encoding": "chunked"},
        ),
        client.post(
            route,
            json=_body(),
            headers=allowed | {"Content-Length": "32769"},
        ),
        client.post(
            "/projects/demo/pages/2147483648/visual-review-evidence",
            json=_body(),
            headers=allowed,
        ),
        client.post(
            "/projects/demo/pages/+1/visual-review-evidence",
            json=_body(),
            headers=allowed,
        ),
        client.post(
            route, json=incomplete, headers=allowed
        ),
        client.post(route, json=duplicate, headers=allowed),
        client.post(route, json=invalid_not_applicable, headers=allowed),
    ) + tuple(
        client.post(route, json=_body() | selector, headers=allowed)
        for selector in selectors
    )

    assert {response.status_code for response in responses} == {422}
    assert calls == 0
    assert all(response.headers["cache-control"] == "no-store" for response in responses)
