from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from manga_director.production.next_generation_page_composition_application_ledger import (
    LocalPageCompositionApplicationLedger,
    PageCompositionApplicationBinding,
)


def _binding(**changes: object) -> PageCompositionApplicationBinding:
    values: dict[str, object] = {
        "application_id": "application-1",
        "project_id": "project-1",
        "page_id": "page-1",
        "page_revision": "revision-1",
        "plan_id": "plan-1",
        "plan_fingerprint": "a" * 64,
        "composition_attempt_id": "composition-1",
        "composition_provenance_reference": "composition-provenance-1",
        "request_fingerprint": "b" * 64,
        "evidence_id": "composition-evidence-1",
        "evidence_sha256": "c" * 64,
        "composite_asset_id": "composite-1",
        "composite_sha256": "d" * 64,
    }
    values.update(changes)
    return PageCompositionApplicationBinding(**values)


def test_prepare_apply_and_exact_replay_are_idempotent(tmp_path: Path) -> None:
    ledger = LocalPageCompositionApplicationLedger(tmp_path / "ledger")
    binding = _binding()
    assert ledger.mark_applied(binding).outcome == "missing"
    assert ledger.prepare(binding).outcome == "prepared"
    assert ledger.prepare(binding).outcome == "confirmed"
    assert ledger.mark_applied(binding).outcome == "applied"
    assert ledger.mark_applied(binding).outcome == "confirmed"
    lookup = ledger.lookup_exact(binding)
    assert lookup.outcome == "confirmed"
    assert lookup.lifecycle == "applied"
    applied = ledger.lookup_applied("project-1", "page-1", "composite-1")
    assert applied.outcome == "found"
    assert applied.binding == binding


def test_page_observation_is_read_only_and_distinguishes_prepared_applied(
    tmp_path: Path,
) -> None:
    missing_root = tmp_path / "missing"
    assert LocalPageCompositionApplicationLedger.observe_page_at(
        missing_root, "project-1", "page-1"
    ).outcome == "missing"
    assert not missing_root.exists()
    missing_root.mkdir()
    assert LocalPageCompositionApplicationLedger.observe_page_at(
        missing_root, "project-1", "page-1"
    ).outcome == "corrupt"

    root = tmp_path / "ledger"
    ledger = LocalPageCompositionApplicationLedger(root)
    binding = _binding()
    ledger.prepare(binding)
    prepared = ledger.observe_page("project-1", "page-1")
    assert prepared.outcome == "prepared"
    assert prepared.plan_ids == ("plan-1",)
    ledger.mark_applied(binding)
    assert ledger.observe_page("project-1", "page-1").outcome == "found"
    with sqlite3.connect(
        root / "page-composition-application-ledger.sqlite3"
    ) as connection:
        connection.execute("PRAGMA user_version = 99")
    assert ledger.observe_page("project-1", "page-1").outcome == "corrupt"


def test_applied_lookup_distinguishes_missing_prepared_and_asset_mismatch(
    tmp_path: Path,
) -> None:
    ledger = LocalPageCompositionApplicationLedger(tmp_path / "ledger")
    assert ledger.lookup_applied("project-1", "page-1", "composite-1").outcome == "missing"
    binding = _binding()
    assert ledger.prepare(binding).outcome == "prepared"
    assert ledger.lookup_applied("project-1", "page-1", "composite-1").outcome == "prepared"
    assert (
        ledger.lookup_applied("project-1", "page-1", "other-composite").outcome
        == "asset_mismatch"
    )


def test_applied_lookup_rejects_multiple_page_revisions(tmp_path: Path) -> None:
    ledger = LocalPageCompositionApplicationLedger(tmp_path / "ledger")
    first = _binding()
    second = _binding(
        application_id="application-2",
        page_revision="revision-2",
        composition_attempt_id="composition-2",
    )
    assert ledger.prepare(first).outcome == "prepared"
    assert ledger.mark_applied(first).outcome == "applied"
    assert ledger.prepare(second).outcome == "prepared"
    assert ledger.mark_applied(second).outcome == "applied"

    result = ledger.lookup_applied("project-1", "page-1", "composite-1")

    assert result.outcome == "ambiguous"
    assert result.binding is None


def test_binding_difference_and_second_page_application_conflict(tmp_path: Path) -> None:
    ledger = LocalPageCompositionApplicationLedger(tmp_path / "ledger")
    assert ledger.prepare(_binding()).outcome == "prepared"
    assert ledger.prepare(_binding(composite_sha256="e" * 64)).outcome == "conflict"
    assert ledger.prepare(
        _binding(application_id="application-2", composition_attempt_id="composition-2")
    ).outcome == "conflict"


def test_concurrent_prepare_has_one_insert_and_one_confirmation(tmp_path: Path) -> None:
    root = tmp_path / "ledger"
    LocalPageCompositionApplicationLedger(root)

    def prepare() -> str:
        return LocalPageCompositionApplicationLedger(root).prepare(_binding()).outcome

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = tuple(executor.map(lambda _: prepare(), range(2)))
    assert sorted(outcomes) == ["confirmed", "prepared"]


def test_corrupt_payload_fails_closed(tmp_path: Path) -> None:
    root = tmp_path / "ledger"
    ledger = LocalPageCompositionApplicationLedger(root)
    binding = _binding()
    assert ledger.prepare(binding).outcome == "prepared"
    with sqlite3.connect(root / "page-composition-application-ledger.sqlite3") as connection:
        connection.execute(
            "UPDATE composition_application SET binding_fingerprint = ?", ("0" * 64,)
        )
    assert ledger.lookup_exact(binding).outcome == "corrupt"
    assert ledger.lookup_applied("project-1", "page-1", "composite-1").outcome == "corrupt"
