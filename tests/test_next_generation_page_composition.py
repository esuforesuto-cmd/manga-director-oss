from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_page_composition import (
    AcceptedPanelSource,
    LocalPageCompositionAuthority,
    PageCompositeAsset,
    PageCompositionAttempt,
    PageCompositionEvidence,
    PageCompositionRequest,
)
from manga_director.production.next_generation_page_generation_plan import PanelRectangle


def _coordinate(pixel: int, size: int) -> int:
    return (pixel * 1_000_000 + size - 1) // size


def _source(panel_id: str, order: int) -> AcceptedPanelSource:
    left, right = ((96, 1000) if order == 1 else (1048, 1952))
    return AcceptedPanelSource(
        plan_id="plan-1",
        plan_fingerprint="a" * 64,
        project_id="project-1",
        page_id="page-1",
        panel_id=panel_id,
        panel_order=order,
        request_id=f"request-{order}",
        request_fingerprint=str(order + 2) * 64,
        attempt_id=f"attempt-{order}",
        evidence_id=f"evidence-{order}",
        asset_id=f"asset-{order}",
        content_sha256=str(order) * 64,
        width=512,
        height=512,
        rectangle=PanelRectangle(
            left=_coordinate(left, 2048),
            top=_coordinate(96, 3072),
            right=_coordinate(right, 2048),
            bottom=_coordinate(2976, 3072),
        ),
    )


def _request(**changes: object) -> PageCompositionRequest:
    values: dict[str, object] = {
        "composition_attempt_id": "composition-1",
        "plan_id": "plan-1",
        "plan_fingerprint": "a" * 64,
        "project_id": "project-1",
        "page_id": "page-1",
        "explicit_authorization_reference": "auth-1",
        "composition_provenance_reference": "composition-provenance-1",
        "panel_count": 2,
        "sources": (_source("panel-1", 1), _source("panel-2", 2)),
    }
    values.update(changes)
    return PageCompositionRequest(**values)


def test_request_fingerprint_binds_canonical_source_order() -> None:
    request = _request()
    assert len(request.request_fingerprint or "") == 64
    assert request.sources[0].panel_order == 1


def test_request_rejects_noncanonical_or_duplicate_sources() -> None:
    with pytest.raises(ValidationError):
        _request(sources=(_source("panel-2", 2), _source("panel-1", 1)))
    with pytest.raises(ValidationError):
        _request(sources=(_source("panel-1", 1), _source("panel-1", 2)))


def test_request_rejects_incomplete_or_reused_source_bindings() -> None:
    with pytest.raises(ValidationError):
        _request(panel_count=3)
    for field in ("request_id", "attempt_id", "evidence_id", "asset_id"):
        duplicate = _source("panel-2", 2).model_copy(
            update={field: getattr(_source("panel-1", 1), field)}
        )
        with pytest.raises(ValidationError):
            _request(sources=(_source("panel-1", 1), duplicate))


def test_composition_evidence_cannot_claim_provider_invocation() -> None:
    with pytest.raises(ValidationError):
        PageCompositionEvidence(
            evidence_id="composition-evidence-1", composition_attempt_id="composition-1",
            plan_id="plan-1", plan_fingerprint="a" * 64,
            project_id="project-1", page_id="page-1", request_fingerprint="b" * 64,
            composition_provenance_reference="composition-provenance-1",
            ordered_sources=(_source("panel-1", 1),), output_asset_id="composite-1",
            output_sha256="c" * 64, outcome="completed", provider_invocation_performed=True,
        )


def test_request_rejects_mixed_plan_or_hash_mismatch() -> None:
    mixed = _source("panel-2", 2).model_copy(update={"plan_id": "plan-2"})
    with pytest.raises(ValidationError):
        _request(sources=(_source("panel-1", 1), mixed))
    request = _request()
    with pytest.raises(ValidationError):
        _request(request_fingerprint="f" * 64)
    assert request.pixel_fit_policy == "cover-center"


def test_request_rejects_aggregate_source_pixel_limit() -> None:
    oversized_sources = tuple(
        source.model_copy(update={"width": 4096, "height": 4096})
        for source in (_source("panel-1", 1), _source("panel-2", 2))
    )
    with pytest.raises(ValidationError):
        _request(sources=oversized_sources)


def test_composition_attempt_binds_ordered_source_manifest() -> None:
    attempt = PageCompositionAttempt(
        composition_attempt_id="composition-1",
        request_fingerprint="a" * 64,
        plan_id="plan-1",
        plan_fingerprint="b" * 64,
        project_id="project-1",
        page_id="page-1",
        explicit_authorization_reference="auth-1",
        composition_provenance_reference="composition-provenance-1",
        ordered_source_asset_ids=("asset-1", "asset-2"),
        ordered_source_hashes=("c" * 64, "d" * 64),
    )
    assert attempt.outcome == "reserved"
    with pytest.raises(ValidationError):
        PageCompositionAttempt(
            **(
                attempt.model_dump()
                | {"ordered_source_hashes": ("c" * 64,)}
            )
        )


def test_composite_asset_rejects_mixed_or_reused_source_manifest() -> None:
    first = _source("panel-1", 1)
    mixed = _source("panel-2", 2).model_copy(update={"plan_id": "plan-2"})
    values: dict[str, object] = {
        "composition_attempt_id": "composition-1",
        "request_fingerprint": "a" * 64,
        "composition_provenance_reference": "composition-provenance-1",
        "ordered_sources": (first, mixed),
        "asset_id": "composite-1",
        "content_sha256": "b" * 64,
    }
    with pytest.raises(ValidationError):
        PageCompositeAsset(**values)
    reused = _source("panel-2", 2).model_copy(update={"attempt_id": first.attempt_id})
    with pytest.raises(ValidationError):
        PageCompositeAsset(**(values | {"ordered_sources": (first, reused)}))


def _completed_evidence(request: PageCompositionRequest) -> PageCompositionEvidence:
    return PageCompositionEvidence(
        evidence_id="composition-evidence-1",
        composition_attempt_id=request.composition_attempt_id,
        plan_id=request.plan_id,
        plan_fingerprint=request.plan_fingerprint,
        project_id=request.project_id,
        page_id=request.page_id,
        request_fingerprint=request.request_fingerprint or "",
        composition_provenance_reference=request.composition_provenance_reference,
        ordered_sources=request.sources,
        output_asset_id="composite-1",
        output_sha256="f" * 64,
        outcome="completed",
    )


def test_composition_authority_reserves_and_commits_exact_evidence(tmp_path: Path) -> None:
    authority = LocalPageCompositionAuthority(tmp_path / "composition")
    request = _request()
    assert authority.reserve(request).outcome == "created"
    assert authority.reserve(request).outcome == "confirmed"
    evidence = _completed_evidence(request)
    committed = authority.commit_evidence(evidence)
    assert committed.outcome == "updated"
    assert committed.attempt is not None and committed.attempt.outcome == "completed"
    assert authority.commit_evidence(evidence).outcome == "confirmed"
    lookup = authority.lookup(request.composition_attempt_id)
    assert lookup.outcome == "confirmed"
    assert lookup.evidence == evidence


def test_composition_authority_rejects_active_duplicate_and_mixed_binding(
    tmp_path: Path,
) -> None:
    authority = LocalPageCompositionAuthority(tmp_path / "composition")
    request = _request()
    assert authority.reserve(request).outcome == "created"
    duplicate = _request(composition_attempt_id="composition-2")
    assert authority.reserve(duplicate).outcome == "conflict"
    mixed = _completed_evidence(request).model_copy(update={"plan_id": "plan-other"})
    assert authority.commit_evidence(mixed).outcome == "conflict"


def test_recovery_required_composition_blocks_replacement_attempt(tmp_path: Path) -> None:
    authority = LocalPageCompositionAuthority(tmp_path / "composition")
    request = _request()
    assert authority.reserve(request).outcome == "created"
    recovery = _completed_evidence(request).model_copy(
        update={
            "output_asset_id": None,
            "output_sha256": None,
            "outcome": "recovery_required",
        }
    )
    assert authority.commit_evidence(recovery).outcome == "updated"
    assert authority.reserve(
        _request(composition_attempt_id="composition-2")
    ).outcome == "conflict"


def test_composition_index_column_tampering_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "composition"
    authority = LocalPageCompositionAuthority(root)
    request = _request()
    assert authority.reserve(request).outcome == "created"
    with sqlite3.connect(root / "page-composition-authority.sqlite3") as connection:
        connection.execute(
            "UPDATE composition_attempts SET outcome = 'completed' "
            "WHERE composition_attempt_id = ?",
            (request.composition_attempt_id,),
        )
    assert authority.lookup(request.composition_attempt_id).outcome == "corrupt"
