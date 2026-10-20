from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from fastapi.testclient import TestClient

from manga_director.api import workflow as workflow_api
from manga_director.api.workflow import create_workflow_app
from manga_director.application.human_visual_review_evidence_history import (
    HumanVisualReviewEvidenceHistoryPersistenceUnavailable,
    HumanVisualReviewEvidenceHistoryService,
    HumanVisualReviewEvidenceHistoryUnavailable,
    build_human_visual_review_evidence_history,
)
from manga_director.application.workflow import WorkflowApplicationService
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production.next_generation_durable_human_visual_review_evidence import (
    LocalDurableHumanVisualReviewEvidenceOwner,
    _EvidenceChecklistItem,
    _HumanVisualReviewEvidencePayload,
)
from manga_director.repositories.local_file import LocalFileRepository

_PROJECT = "project-v7-11"
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
_HISTORY_HEADERS = {
    "Origin": "http://127.0.0.1:3000",
    "Referer": "http://127.0.0.1:3000/projects/project-v7-11/pages/1",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Accept": "application/json",
}


def _payload(review_id: str = "review:v7-11:001") -> _HumanVisualReviewEvidencePayload:
    return _HumanVisualReviewEvidencePayload(
        review_id=review_id,
        project_id=_PROJECT,
        page_id="1",
        page_number=1,
        page_state="QualityChecked",
        attempt_id="attempt:v7-11:001",
        output_asset_id="asset:v7-11:001",
        provenance_reference="provenance:v7-11:001",
        qa_report_reference="qa-report:v7-11:001",
        reviewer_id="reviewer:local",
        reviewed_at=datetime(2026, 10, 20, 12, 0, tzinfo=UTC),
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


def _repository(tmp_path: Path, state: PageState) -> LocalFileRepository:
    repository = LocalFileRepository(tmp_path / "repository")
    generated = state in {
        PageState.GENERATED,
        PageState.QUALITY_CHECKED,
        PageState.APPROVED,
    }
    repository.save(
        Project(
            id=_PROJECT,
            title="V7-11",
            pages=[
                Page(
                    page_number=1,
                    state=state,
                    page_design={} if generated else None,
                    review={} if generated else None,
                    storyboard={} if generated else None,
                    prompt={} if generated else None,
                    image={
                        "artifact_kind": "logical_output_asset",
                        "output_asset_id": "asset:v7-11:001",
                    }
                    if generated
                    else None,
                    quality={}
                    if state in {PageState.QUALITY_CHECKED, PageState.APPROVED}
                    else None,
                    approval={} if state is PageState.APPROVED else None,
                )
            ],
        )
    )
    if generated:
        repository._next_generation_normal_execution_owner_root().mkdir(
            parents=True,
            exist_ok=True,
        )
    return repository


def _manifest(root: Path) -> dict[str, tuple[bytes, int]]:
    return {
        path.relative_to(root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file()
    }


def _http_record() -> SimpleNamespace:
    return SimpleNamespace(
        review_id="review:v7-11:001",
        output_asset_id="asset:v7-11:001",
        reviewer_id="reviewer:local",
        reviewed_at=datetime(2026, 10, 20, 12, 0, tzinfo=UTC),
        page_state="QualityChecked",
        checklist=tuple(
            SimpleNamespace(
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


@pytest.mark.parametrize(
    "state",
    (PageState.GENERATED, PageState.QUALITY_CHECKED, PageState.APPROVED),
)
def test_application_returns_complete_history_without_mutation(
    tmp_path: Path,
    state: PageState,
) -> None:
    repository = _repository(tmp_path, state)
    owner = LocalDurableHumanVisualReviewEvidenceOwner(
        repository._next_generation_normal_execution_owner_root()
    )
    owner.persist(_payload("review:v7-11:002"))
    owner.persist(_payload("review:v7-11:001"))
    service = build_human_visual_review_evidence_history(repository)
    before = _manifest(repository._root)

    result = service.get(_PROJECT, 1)

    assert result.page_number == 1
    assert result.complete is True
    assert result.read_only is True
    assert result.analysis_only is True
    assert tuple(record.review_id for record in result.records) == (
        "review:v7-11:001",
        "review:v7-11:002",
    )
    assert all(record.page_state == "QualityChecked" for record in result.records)
    assert _manifest(repository._root) == before
    assert repository.load(_PROJECT).page(1).state is state


def test_application_absent_store_is_empty_and_earlier_state_fails_closed(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path / "empty", PageState.QUALITY_CHECKED)
    service = build_human_visual_review_evidence_history(repository)
    before = _manifest(repository._root)

    result = service.get(_PROJECT, 1)

    assert result.records == ()
    assert _manifest(repository._root) == before
    assert not (
        repository._next_generation_normal_execution_owner_root() / "review-evidence"
    ).exists()

    draft_repository = _repository(tmp_path / "draft", PageState.DRAFT)
    draft_service = build_human_visual_review_evidence_history(draft_repository)
    draft_before = _manifest(draft_repository._root)
    with pytest.raises(HumanVisualReviewEvidenceHistoryUnavailable):
        draft_service.get(_PROJECT, 1)
    assert _manifest(draft_repository._root) == draft_before


def test_application_redacts_owner_failure(tmp_path: Path) -> None:
    repository = _repository(tmp_path, PageState.QUALITY_CHECKED)

    class Owner:
        def read_page_history(self, *_args: object) -> None:
            from manga_director.production.next_generation_durable_human_visual_review_evidence import (
                DurableHumanVisualReviewEvidenceUnavailable,
            )

            raise DurableHumanVisualReviewEvidenceUnavailable("private database path")

    service = HumanVisualReviewEvidenceHistoryService(repository, cast(object, Owner()))

    with pytest.raises(
        HumanVisualReviewEvidenceHistoryPersistenceUnavailable,
        match="persistence is unavailable",
    ) as captured:
        service.get(_PROJECT, 1)
    assert "private database path" not in str(captured.value)


def test_http_get_returns_only_closed_complete_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, int]] = []

    def get(project_id: str, page_number: int) -> SimpleNamespace:
        calls.append((project_id, page_number))
        return SimpleNamespace(page_number=page_number, records=(_http_record(),))

    monkeypatch.setattr(
        workflow_api,
        "human_visual_review_evidence_history_for",
        lambda _application: SimpleNamespace(get=get),
    )
    client = TestClient(create_workflow_app(cast(WorkflowApplicationService, object())))

    response = client.get(
        f"/projects/{_PROJECT}/pages/1/visual-review-evidence",
        headers=_HISTORY_HEADERS,
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert {
        "etag",
        "last-modified",
        "location",
        "content-location",
        "content-disposition",
    }.isdisjoint(response.headers)
    assert calls == [(_PROJECT, 1)]
    assert response.json() == {
        "pageNumber": 1,
        "recordCount": 1,
        "complete": True,
        "readOnly": True,
        "analysisOnly": True,
        "records": [
            {
                "reviewId": "review:v7-11:001",
                "outputAssetId": "asset:v7-11:001",
                "reviewerId": "reviewer:local",
                "reviewedAt": "2026-10-20T12:00:00Z",
                "pageState": "QualityChecked",
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
                "status": "ready",
                "ready": True,
                "findings": [],
                "missingPrerequisites": [],
                "analysisOnly": True,
            }
        ],
    }
    assert not any(
        value in response.text.lower()
        for value in (
            "project-v7-11",
            "page_id",
            "attempt",
            "provenance",
            "qa-report",
            "digest",
            "sqlite",
            "approvedby",
            "downloadeligibility",
        )
    )


@pytest.mark.parametrize(
    ("path", "headers", "body"),
    (
        (
            f"/projects/{_PROJECT}/pages/1/visual-review-evidence?reviewId=other",
            _HISTORY_HEADERS,
            None,
        ),
        (
            f"/projects/{_PROJECT}/pages/01/visual-review-evidence",
            _HISTORY_HEADERS,
            None,
        ),
        (
            f"/projects/{_PROJECT}/pages/2147483648/visual-review-evidence",
            _HISTORY_HEADERS,
            None,
        ),
        (
            f"/projects/{_PROJECT}/pages/1/visual-review-evidence",
            {key: value for key, value in _HISTORY_HEADERS.items() if key != "Origin"},
            None,
        ),
        (
            f"/projects/{_PROJECT}/pages/1/visual-review-evidence",
            _HISTORY_HEADERS | {"Range": "bytes=0-1"},
            None,
        ),
        (
            f"/projects/{_PROJECT}/pages/1/visual-review-evidence",
            _HISTORY_HEADERS | {"If-None-Match": '"review-history"'},
            None,
        ),
        (
            f"/projects/{_PROJECT}/pages/1/visual-review-evidence",
            _HISTORY_HEADERS | {"Transfer-Encoding": "chunked"},
            None,
        ),
        (
            f"/projects/{_PROJECT}/pages/1/visual-review-evidence",
            _HISTORY_HEADERS,
            b"{}",
        ),
    ),
)
def test_http_get_rejects_unbounded_or_ambiguous_requests_before_service(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
    headers: dict[str, str],
    body: bytes | None,
) -> None:
    calls = 0

    def get(*_args: object) -> None:
        nonlocal calls
        calls += 1

    monkeypatch.setattr(
        workflow_api,
        "human_visual_review_evidence_history_for",
        lambda _application: SimpleNamespace(get=get),
    )
    client = TestClient(create_workflow_app(cast(WorkflowApplicationService, object())))

    response = client.request("GET", path, headers=headers, content=body)

    assert response.status_code == 422
    assert response.json() == {
        "code": "invalid_input",
        "message": "Request validation failed.",
    }
    assert calls == 0
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("header_name", tuple(_HISTORY_HEADERS))
def test_http_get_rejects_duplicate_admission_header_before_service(
    monkeypatch: pytest.MonkeyPatch,
    header_name: str,
) -> None:
    calls = 0

    def get(*_args: object) -> None:
        nonlocal calls
        calls += 1

    monkeypatch.setattr(
        workflow_api,
        "human_visual_review_evidence_history_for",
        lambda _application: SimpleNamespace(get=get),
    )
    client = TestClient(create_workflow_app(cast(WorkflowApplicationService, object())))
    headers = list(_HISTORY_HEADERS.items()) + [
        (header_name, _HISTORY_HEADERS[header_name])
    ]

    response = client.get(
        f"/projects/{_PROJECT}/pages/1/visual-review-evidence",
        headers=headers,
    )

    assert response.status_code == 422
    assert calls == 0


def test_http_get_redacts_storage_failure_and_enforces_response_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TestClient(create_workflow_app(cast(WorkflowApplicationService, object())))
    path = f"/projects/{_PROJECT}/pages/1/visual-review-evidence"

    def unavailable(*_args: object) -> None:
        raise HumanVisualReviewEvidenceHistoryPersistenceUnavailable(
            "C:/private/review-evidence.sqlite3"
        )

    monkeypatch.setattr(
        workflow_api,
        "human_visual_review_evidence_history_for",
        lambda _application: SimpleNamespace(get=unavailable),
    )
    failure = client.get(path, headers=_HISTORY_HEADERS)
    assert failure.status_code == 503
    assert failure.json() == {
        "code": "history_unavailable",
        "message": "History unavailable.",
    }
    assert "private" not in failure.text.lower()
    assert "sqlite" not in failure.text.lower()

    monkeypatch.setattr(
        workflow_api,
        "human_visual_review_evidence_history_for",
        lambda _application: SimpleNamespace(
            get=lambda *_args: SimpleNamespace(page_number=1, records=(_http_record(),))
        ),
    )
    baseline = client.get(path, headers=_HISTORY_HEADERS)
    assert baseline.status_code == 200
    monkeypatch.setattr(
        workflow_api,
        "_VISUAL_REVIEW_HISTORY_MAX_RESPONSE_BYTES",
        len(baseline.content),
    )
    at_limit = client.get(path, headers=_HISTORY_HEADERS)
    assert at_limit.status_code == 200
    monkeypatch.setattr(
        workflow_api,
        "_VISUAL_REVIEW_HISTORY_MAX_RESPONSE_BYTES",
        len(baseline.content) - 1,
    )
    oversized = client.get(path, headers=_HISTORY_HEADERS)
    assert oversized.status_code == 503
    assert oversized.json()["code"] == "history_unavailable"
