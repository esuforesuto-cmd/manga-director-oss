from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_panel_execution_attempt import (
    PanelAttemptReservation,
)
from manga_director.production.next_generation_panel_generation_evidence import (
    LocalPanelGenerationAuthority,
    PanelAsset,
    PanelGenerationEvidence,
)


def _evidence(**changes: object) -> PanelGenerationEvidence:
    values: dict[str, object] = {
        "evidence_id": "evidence-1", "plan_id": "plan-1", "plan_fingerprint": "a" * 64,
        "project_id": "project-1", "page_id": "page-1", "panel_id": "panel-1", "panel_order": 1,
        "request_id": "request-1", "request_fingerprint": "e" * 64,
        "attempt_id": "attempt-1", "input_reference": "input-1",
        "input_sha256": "b" * 64, "provider_reference": "provider-1",
        "provider_configuration_fingerprint": "c" * 64, "provenance_reference": "provenance-1",
        "output_asset_id": "asset-1", "output_sha256": "d" * 64, "media_type": "image/png",
        "width": 512, "height": 512, "outcome": "accepted", "attempt_state": "PANEL_ACCEPTED",
    }
    values.update(changes)
    return PanelGenerationEvidence(**values)


def _reservation(**changes: object) -> PanelAttemptReservation:
    values: dict[str, object] = {
        "attempt_id": "attempt-1",
        "plan_id": "plan-1",
        "plan_fingerprint": "a" * 64,
        "project_id": "project-1",
        "page_id": "page-1",
        "panel_id": "panel-1",
        "panel_order": 1,
        "request_id": "request-1",
        "request_fingerprint": "e" * 64,
        "provider_reference": "provider-1",
        "authorization_reference": "authorization-1",
        "execution_fingerprint": "f" * 64,
    }
    values.update(changes)
    return PanelAttemptReservation(**values)


def test_accepted_evidence_binds_one_panel_attempt_and_asset() -> None:
    evidence = _evidence()
    assert evidence.attempt_id == "attempt-1"
    assert evidence.output_asset_id == "asset-1"


def test_evidence_rejects_provider_paths_and_invalid_hashes() -> None:
    with pytest.raises(ValidationError):
        _evidence(provider_reference="https://example.invalid")
    with pytest.raises(ValidationError):
        _evidence(output_sha256="not-a-hash")
    with pytest.raises(ValidationError):
        _evidence(request_fingerprint="not-a-hash")


def test_evidence_rejects_out_of_bound_dimensions() -> None:
    with pytest.raises(ValidationError):
        _evidence(width=4097)


def test_failure_evidence_cannot_alias_an_accepted_output() -> None:
    with pytest.raises(ValidationError):
        _evidence(outcome="declared_failure", attempt_state="DECLARED_FAILURE")
    failure = _evidence(
        outcome="declared_failure",
        attempt_state="DECLARED_FAILURE",
        output_asset_id=None,
        output_sha256=None,
        media_type=None,
        width=None,
        height=None,
    )
    assert failure.output_asset_id is None


def test_panel_asset_binds_exact_plan_page_panel_and_attempt() -> None:
    asset = PanelAsset(
        asset_id="asset-1",
        plan_id="plan-1",
        plan_fingerprint="a" * 64,
        project_id="project-1",
        page_id="page-1",
        panel_id="panel-1",
        panel_order=1,
        request_id="request-1",
        request_fingerprint="e" * 64,
        attempt_id="attempt-1",
        width=512,
        height=512,
        content_sha256="d" * 64,
    )
    assert asset.media_type == "image/png"


def test_panel_authority_persists_exact_lifecycle_and_evidence(tmp_path: Path) -> None:
    authority = LocalPanelGenerationAuthority(tmp_path / "panels")
    reservation = _reservation()
    assert authority.reserve(reservation).outcome == "created"
    assert authority.reserve(reservation).outcome == "confirmed"
    assert authority.start_provider(reservation).outcome == "updated"
    assert authority.start_provider(reservation).outcome == "confirmed"
    assert authority.record_provider_completed(reservation).outcome == "updated"
    assert authority.record_asset_registered(reservation, "asset-1").outcome == "updated"
    assert authority.commit_evidence(reservation, _evidence()).outcome == "updated"
    assert authority.commit_evidence(reservation, _evidence()).outcome == "confirmed"
    accepted = authority.accept_panel(reservation)
    assert accepted.outcome == "updated"
    assert accepted.record is not None
    assert accepted.record.state == "PANEL_ACCEPTED"
    assert authority.accept_panel(reservation).outcome == "confirmed"


def test_only_one_nonterminal_attempt_per_plan_panel(tmp_path: Path) -> None:
    authority = LocalPanelGenerationAuthority(tmp_path / "panels")
    first = _reservation()
    second = _reservation(attempt_id="attempt-2")
    assert authority.reserve(first).outcome == "created"
    assert authority.reserve(second).outcome == "conflict"
    assert authority.start_provider(first).outcome == "updated"
    assert authority.declare_failure(first).outcome == "updated"
    assert authority.reserve(second).outcome == "created"


def test_mixed_plan_and_tampered_index_columns_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "panels"
    authority = LocalPanelGenerationAuthority(root)
    first = _reservation()
    authority.reserve(first)
    authority.start_provider(first)
    authority.declare_failure(first)
    assert authority.reserve(
        _reservation(attempt_id="attempt-2", plan_id="plan-2")
    ).outcome == "conflict"
    with sqlite3.connect(root / "panel-generation-authority.sqlite3") as connection:
        connection.execute(
            "UPDATE panel_attempts SET state = 'PANEL_ACCEPTED' WHERE attempt_id = ?",
            (first.attempt_id,),
        )
    assert authority.lookup_attempt(first.attempt_id).outcome == "corrupt"


def test_evidence_mismatch_and_unsafe_recovery_fail_closed(tmp_path: Path) -> None:
    authority = LocalPanelGenerationAuthority(tmp_path / "panels")
    reservation = _reservation()
    authority.reserve(reservation)
    authority.start_provider(reservation)
    authority.record_provider_completed(reservation)
    authority.record_asset_registered(reservation, "asset-1")
    assert authority.commit_evidence(
        reservation, _evidence(output_asset_id="asset-other")
    ).outcome == "conflict"
    assert authority.start_provider(reservation).outcome == "conflict"
    recovery = authority.require_recovery(reservation)
    assert recovery.outcome == "updated"
    assert recovery.record is not None and recovery.record.state == "RECOVERY_REQUIRED"
    assert authority.reserve(_reservation(attempt_id="attempt-2")).outcome == "conflict"
    reconciled = authority.commit_evidence(reservation, _evidence())
    assert reconciled.outcome == "updated"
    assert authority.accept_panel(reservation).outcome == "updated"
