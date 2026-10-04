"""Focused R30 pre-CAS provenance sidecar tests."""

from __future__ import annotations

import sqlite3
from dataclasses import replace

import pytest

from manga_director.production.future_real_delivery_r30_pre_cas_ledger_provenance import (
    _canonical_r30_pre_cas_provenance_v1,
    _construct_r30_pre_cas_ledger_provenance_store_v1,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    WorkflowApplicationLedgerBindingDTO,
)
from manga_director.repositories.local_file import LocalFileRepository


def _binding() -> WorkflowApplicationLedgerBindingDTO:
    return WorkflowApplicationLedgerBindingDTO(
        attempt_id="attempt-r30-001",
        authorization_id="authorization-r30-001",
        project_id="project-r30-001",
        page_id="1",
        target_page_reference="page:1",
        provider_reference="provider-r30-001",
        output_asset_id="asset-r30-001",
        source_state="PromptBuilt",
        target_state="Generated",
    )


def test_sidecar_create_once_exact_replay_and_readonly_reopen(tmp_path) -> None:
    repository = LocalFileRepository(tmp_path)
    repository._root.mkdir(parents=True)
    store = _construct_r30_pre_cas_ledger_provenance_store_v1(repository)
    record = _canonical_r30_pre_cas_provenance_v1(
        _binding(), expected_pre_cas_revision=1, expected_pre_cas_fingerprint="a" * 64
    )

    assert store._create_or_confirm_v1(record)[0] == "CREATED"
    assert store._create_or_confirm_v1(record)[0] == "EXACT_REPLAY"
    assert store._read_exact_v1(_binding()) == record
    reopened = _construct_r30_pre_cas_ledger_provenance_store_v1(repository)
    assert reopened._read_exact_v1(_binding()) == record


def test_sidecar_conflict_and_corruption_fail_closed(tmp_path) -> None:
    repository = LocalFileRepository(tmp_path)
    repository._root.mkdir(parents=True)
    store = _construct_r30_pre_cas_ledger_provenance_store_v1(repository)
    record = _canonical_r30_pre_cas_provenance_v1(
        _binding(), expected_pre_cas_revision=1, expected_pre_cas_fingerprint="a" * 64
    )
    assert store._create_or_confirm_v1(record)[0] == "CREATED"
    assert store._create_or_confirm_v1(replace(record, record_digest="b" * 64))[0] == "CONFLICT"

    with sqlite3.connect(store._database_path) as connection:
        connection.execute("DELETE FROM r30_pre_cas_ledger_provenance_schema_meta")
        connection.commit()
    with pytest.raises(ValueError, match="CORRUPT"):
        _construct_r30_pre_cas_ledger_provenance_store_v1(repository)
