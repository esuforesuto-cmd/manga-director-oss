"""Adversarial focused tests for the private R21 Ledger observer."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from manga_director.production import next_generation_workflow_application_ledger as ledger_module
from manga_director.production.future_real_delivery_r21_ledger_observation import (
    _bind_exact_localfile_ledger_observer_v1,
    _construct_localfile_ledger_observation_composition_v1,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    LocalWorkflowApplicationLedgerStore,
    WorkflowApplicationLedgerBindingDTO,
    _authoritative_commit_proof,
)
from manga_director.repositories.local_file import LocalFileRepository


def _binding(**updates: str) -> WorkflowApplicationLedgerBindingDTO:
    values: dict[str, object] = {
        "attempt_id": "attempt:r21:001",
        "authorization_id": "authorization:r21:001",
        "project_id": "project:r21:001",
        "page_id": "1",
        "target_page_reference": "page:r21:001",
        "provider_reference": "provider:fake:r21",
        "output_asset_id": "asset:r21:001",
        "source_state": "PromptBuilt",
        "target_state": "Generated",
    }
    values.update(updates)
    return WorkflowApplicationLedgerBindingDTO.model_validate(values)


def _composition(
    tmp_path: Path,
) -> tuple[object, LocalFileRepository, LocalWorkflowApplicationLedgerStore]:
    composition = _construct_localfile_ledger_observation_composition_v1(tmp_path)
    return composition, composition._repository, composition._ledger_store


def _observe(
    composition: object,
    repository: object,
    store: object,
    binding: object,
) -> str:
    observer = _bind_exact_localfile_ledger_observer_v1(composition, repository, store)
    return observer._observe_exact_readonly_v1(binding).outcome


def _database(store: LocalWorkflowApplicationLedgerStore) -> Path:
    return store._database_path


def test_r21_observes_missing_prepared_and_applied_without_mutation(tmp_path: Path) -> None:
    composition, repository, store = _composition(tmp_path)
    binding = _binding()

    assert _observe(composition, repository, store, binding) == "MISSING"
    assert store.prepare(binding).outcome == "prepared"
    before = _database(store).read_bytes()
    assert _observe(composition, repository, store, binding) == "PREPARED"
    assert _database(store).read_bytes() == before
    assert store.finalize(binding, _authoritative_commit_proof(binding)).outcome == "applied"
    assert _observe(composition, repository, store, binding) == "APPLIED"


def test_r21_accepts_an_equivalent_copied_dto_as_query_value(tmp_path: Path) -> None:
    composition, repository, store = _composition(tmp_path)
    binding = _binding()
    assert store.prepare(binding).outcome == "prepared"
    copied = WorkflowApplicationLedgerBindingDTO.model_validate(binding.model_dump())

    assert copied is not binding
    assert _observe(composition, repository, store, copied) == "PREPARED"


def test_r21_rejects_invalid_or_non_exact_observation_inputs_before_access(tmp_path: Path) -> None:
    composition, repository, store = _composition(tmp_path)
    before = _database(store).read_bytes()

    assert _observe(composition, repository, store, {"attempt_id": "claim"}) == "AUTHORITY_REJECTED"
    assert _observe(composition, object(), store, _binding()) == "AUTHORITY_REJECTED"
    assert _observe(composition, repository, object(), _binding()) == "AUTHORITY_REJECTED"
    assert _database(store).read_bytes() == before


def test_r21_rejects_a_different_localfile_owner_root_before_access(tmp_path: Path) -> None:
    composition, repository, store = _composition(tmp_path / "first")
    replacement_repository = LocalFileRepository(tmp_path / "second")
    before = _database(store).read_bytes()

    assert _observe(composition, replacement_repository, store, _binding()) == "AUTHORITY_REJECTED"
    assert _database(store).read_bytes() == before


def test_r21_rejects_a_same_root_replacement_store_before_sqlite_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    composition, repository, store = _composition(tmp_path)
    replacement = LocalWorkflowApplicationLedgerStore(repository._workflow_application_ledger_owner_root())
    before = _database(store).read_bytes()
    observed = False

    def _forbidden_observation(
        self: LocalWorkflowApplicationLedgerStore,
        binding: object,
    ) -> object:
        del self, binding
        nonlocal observed
        observed = True
        raise AssertionError("replacement SQLite observation must not occur")

    monkeypatch.setattr(
        LocalWorkflowApplicationLedgerStore,
        "_observe_exact_readonly_v1",
        _forbidden_observation,
    )
    assert replacement is not store

    assert _observe(composition, repository, replacement, _binding()) == "AUTHORITY_REJECTED"
    assert not observed
    assert _database(store).read_bytes() == before


def test_r21_rejects_a_same_root_replacement_repository_before_sqlite_access(tmp_path: Path) -> None:
    composition, repository, store = _composition(tmp_path)
    replacement = LocalFileRepository(tmp_path)
    before = _database(store).read_bytes()
    assert replacement is not repository

    assert _observe(composition, replacement, store, _binding()) == "AUTHORITY_REJECTED"
    assert _database(store).read_bytes() == before


def test_r21_rejects_a_different_root_replacement_store_before_sqlite_access(tmp_path: Path) -> None:
    composition, repository, store = _composition(tmp_path / "first")
    replacement = LocalWorkflowApplicationLedgerStore(
        LocalFileRepository(tmp_path / "second")._workflow_application_ledger_owner_root()
    )
    before = _database(store).read_bytes()

    assert _observe(composition, repository, replacement, _binding()) == "AUTHORITY_REJECTED"
    assert _database(store).read_bytes() == before


def test_r21_rejects_a_cross_composition_pair_before_sqlite_access(tmp_path: Path) -> None:
    composition, repository, store = _composition(tmp_path / "first")
    _, other_repository, other_store = _composition(tmp_path / "second")
    before = _database(store).read_bytes()

    assert _observe(composition, other_repository, other_store, _binding()) == "AUTHORITY_REJECTED"
    assert _database(store).read_bytes() == before


def test_r21_classifies_two_exact_selector_rows_as_conflict(tmp_path: Path) -> None:
    composition, repository, store = _composition(tmp_path)
    requested = _binding()
    by_attempt = _binding(authorization_id="authorization:r21:other")
    by_authorization = _binding(attempt_id="attempt:r21:other")
    assert store.prepare(by_attempt).outcome == "prepared"
    assert store.prepare(by_authorization).outcome == "prepared"

    assert _observe(composition, repository, store, requested) == "CONFLICT"


def test_r21_classifies_selected_binding_mismatch_as_conflict(tmp_path: Path) -> None:
    composition, repository, store = _composition(tmp_path)
    persisted = _binding(project_id="project:r21:other")
    assert store.prepare(persisted).outcome == "prepared"

    assert _observe(composition, repository, store, _binding()) == "CONFLICT"


def test_r21_classifies_schema_and_row_integrity_mismatches_as_corrupt(tmp_path: Path) -> None:
    composition, repository, store = _composition(tmp_path)
    binding = _binding()
    assert store.prepare(binding).outcome == "prepared"
    with sqlite3.connect(_database(store)) as connection:
        connection.execute("UPDATE workflow_application_ledger SET binding_digest = 'tampered'")
    assert _observe(composition, repository, store, binding) == "CORRUPT"

    other_composition, other_repository, other_store = _composition(tmp_path / "schema")
    with sqlite3.connect(_database(other_store)) as connection:
        connection.execute("CREATE TABLE unexpected_r21_table (id TEXT PRIMARY KEY)")
    assert _observe(other_composition, other_repository, other_store, binding) == "CORRUPT"


def test_r21_classifies_not_a_database_as_corrupt(tmp_path: Path) -> None:
    composition, repository, store = _composition(tmp_path)
    _database(store).write_bytes(b"not sqlite")

    assert _observe(composition, repository, store, _binding()) == "CORRUPT"


def test_r21_classifies_missing_database_as_recovery_required(tmp_path: Path) -> None:
    composition, repository, store = _composition(tmp_path)
    _database(store).unlink()

    assert _observe(composition, repository, store, _binding()) == "RECOVERY_REQUIRED"


@pytest.mark.parametrize(
    "error",
    (
        sqlite3.OperationalError("database is busy"),
        sqlite3.OperationalError("database is locked"),
        OSError("I/O"),
        PermissionError("access denied"),
    ),
)
def test_r21_classifies_transient_open_failures_as_recovery_required(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    composition, repository, store = _composition(tmp_path)

    def _raising_open(_: Path) -> sqlite3.Connection:
        raise error

    monkeypatch.setattr(ledger_module, "_open_r21_readonly_connection", _raising_open)
    assert _observe(composition, repository, store, _binding()) == "RECOVERY_REQUIRED"


def test_r21_requires_query_only_and_never_executes_a_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    composition, repository, store = _composition(tmp_path)
    statements: list[str] = []
    original_open = ledger_module._open_r21_readonly_connection

    def _traced_open(path: Path) -> sqlite3.Connection:
        connection = original_open(path)
        connection.set_trace_callback(statements.append)
        return connection

    monkeypatch.setattr(ledger_module, "_open_r21_readonly_connection", _traced_open)
    assert _observe(composition, repository, store, _binding()) == "MISSING"
    normalized = "\n".join(statements).upper()
    assert "PRAGMA QUERY_ONLY = ON" in normalized
    assert "BEGIN" in normalized
    assert not any(keyword in normalized for keyword in ("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER"))


def test_r21_reopen_remains_readonly_and_deterministic(tmp_path: Path) -> None:
    composition, repository, store = _composition(tmp_path)
    binding = _binding()
    assert store.prepare(binding).outcome == "prepared"
    before = _database(store).read_bytes()
    reopened_composition, reopened_repository, reopened = _composition(tmp_path)

    assert _observe(reopened_composition, reopened_repository, reopened, binding) == "PREPARED"
    assert _database(reopened).read_bytes() == before
