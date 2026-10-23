from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_page_generation_mode_claim import (
    LocalPageGenerationModeClaimStore,
    PageGenerationModeClaim,
)


def _claim(**changes: object) -> PageGenerationModeClaim:
    values: dict[str, object] = {
        "claim_id": "claim-1",
        "project_id": "project-1",
        "page_id": "page-1",
        "page_revision": "revision-1",
        "page_fingerprint": "a" * 64,
        "mode": "panel_aware",
        "mode_binding_reference": "plan-1",
        "authorizer_reference": "authorization-1",
    }
    values.update(changes)
    return PageGenerationModeClaim(**values)


def test_claim_fingerprint_is_canonical_and_immutable() -> None:
    claim = _claim()
    assert len(claim.binding_fingerprint or "") == 64
    with pytest.raises(ValidationError):
        _claim(binding_fingerprint="f" * 64)
    with pytest.raises(ValidationError):
        claim.mode = "legacy_single_canvas"  # type: ignore[misc]


def test_exact_replay_confirms_but_other_mode_or_revision_conflicts(tmp_path: Path) -> None:
    store = LocalPageGenerationModeClaimStore(tmp_path / "claims")
    claim = _claim()

    assert store.create_or_confirm(claim).outcome == "created"
    assert store.create_or_confirm(claim).outcome == "confirmed"
    assert store.create_or_confirm(
        _claim(claim_id="claim-2", mode="legacy_single_canvas", mode_binding_reference="attempt-1")
    ).outcome == "conflict"
    assert store.create_or_confirm(
        _claim(claim_id="claim-3", page_revision="revision-2")
    ).outcome == "conflict"
    lookup = store.lookup_active("project-1", "page-1", "revision-1")
    assert lookup.outcome == "found"
    assert lookup.claim == claim
    assert store.lookup_active("project-1", "page-1", "revision-2").outcome == "corrupt"


def test_concurrent_conflicting_claims_have_one_durable_winner(tmp_path: Path) -> None:
    root = tmp_path / "claims"
    LocalPageGenerationModeClaimStore(root)
    claims = (
        _claim(),
        _claim(
            claim_id="claim-2",
            mode="legacy_single_canvas",
            mode_binding_reference="legacy-attempt-1",
        ),
    )

    def persist(claim: PageGenerationModeClaim) -> str:
        return LocalPageGenerationModeClaimStore(root).create_or_confirm(claim).outcome

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = tuple(executor.map(persist, claims))

    assert sorted(outcomes) == ["conflict", "created"]


def test_unknown_schema_and_tampered_payload_fail_closed(tmp_path: Path) -> None:
    root = tmp_path / "claims"
    store = LocalPageGenerationModeClaimStore(root)
    assert store.create_or_confirm(_claim()).outcome == "created"
    database = root / "page-generation-mode-claims.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE page_generation_mode_claims SET binding_fingerprint = ?", ("0" * 64,)
        )
    assert store.lookup_active("project-1", "page-1", "revision-1").outcome == "corrupt"
    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA user_version = 99")
    with pytest.raises(ValueError):
        LocalPageGenerationModeClaimStore(root)
