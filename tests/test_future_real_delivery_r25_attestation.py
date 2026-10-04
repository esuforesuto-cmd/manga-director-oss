from __future__ import annotations

import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from manga_director.production.future_real_delivery_r25_attestation import (
    _canonical_r25_record_v1,
    _construct_r25_attestation_store_v1,
    _construct_r25_materialization_service_v1,
    _R25AttestationStoreV1,
    _R25CanonicalRecordV1,
    _R25MaterializationRequestV1,
    _R25MaterializationServiceV1,
)
from manga_director.repositories.local_file import LocalFileRepository


def _repository(tmp_path: Path) -> LocalFileRepository:
    root = tmp_path / "repository"
    (root / "projects").mkdir(parents=True)
    return LocalFileRepository(root)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _canonical_record(*, output_asset_id: str = "output-asset-1") -> _R25CanonicalRecordV1:
    application_binding_json = json.dumps(
        {
            "application_id": "application-1",
            "attempt_id": "attempt-1",
            "page_id": "page-1",
            "project_id": "project-1",
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return _canonical_r25_record_v1(
        delivery_identity="a" * 64,
        attempt_id="attempt-1",
        application_binding_digest=_sha256(application_binding_json),
        project_id="project-1",
        page_id="page-1",
        target_page_reference="page-1",
        provider_reference="provider-1",
        authorization_id="authorization-1",
        output_asset_id=output_asset_id,
        canonical_result_identity="canonical-result-1",
        logical_output_id="logical-output-1",
        asset_identity="asset-1",
        asset_sha256="b" * 64,
        expected_byte_length=42,
        evidence_identity="c" * 64,
        evidence_persistence_digest="d" * 64,
        evidence_binding_fingerprint="e" * 64,
        pre_commit_revision=1,
        pre_commit_fingerprint="f" * 64,
        post_commit_revision=2,
        post_commit_fingerprint="0" * 64,
        application_binding_json=application_binding_json,
    )


def test_store_uses_fixed_localfile_owned_path_and_reopens(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    store = _construct_r25_attestation_store_v1(repository)

    assert store._database_path == (
        repository._root.resolve()
        / "_durability"
        / "_post_cas_application_attestations"
        / "post-cas-application-attestations.sqlite3"
    )
    assert store._database_path.is_file()
    assert _construct_r25_attestation_store_v1(repository)._database_path == store._database_path


def test_store_rejects_direct_construction_and_non_localfile_owner(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        _R25AttestationStoreV1()
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        _construct_r25_attestation_store_v1(tmp_path)


def test_reopen_rejects_extra_schema_object(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    store = _construct_r25_attestation_store_v1(repository)
    connection = sqlite3.connect(store._database_path)
    try:
        connection.execute("CREATE TABLE unexpected (value TEXT)")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(ValueError, match="CORRUPT"):
        _construct_r25_attestation_store_v1(repository)


def test_reopen_rejects_zero_byte_store(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    store = _construct_r25_attestation_store_v1(repository)
    store._database_path.write_bytes(b"")

    with pytest.raises(ValueError, match="CORRUPT"):
        _construct_r25_attestation_store_v1(repository)


def test_missing_row_creates_once_and_exact_row_replays_after_reopen(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    store = _construct_r25_attestation_store_v1(repository)
    record = _canonical_record()

    result, persisted = store._create_or_confirm_v1(record)

    assert result == "ATTESTED"
    assert persisted == record
    reopened = _construct_r25_attestation_store_v1(repository)
    replay = reopened._replay_post_cas_attestation_exact_v1(record.values[3])
    assert replay == record
    result, persisted = reopened._create_or_confirm_v1(record)
    assert result == "ATTESTED_REPLAY"
    assert persisted == record
    connection = sqlite3.connect(reopened._database_path)
    try:
        assert connection.execute("SELECT COUNT(*) FROM post_cas_application_attestations").fetchone() == (1,)
    finally:
        connection.close()


def test_conflicting_immutable_row_is_rejected_without_overwrite(tmp_path: Path) -> None:
    store = _construct_r25_attestation_store_v1(_repository(tmp_path))
    record = _canonical_record()
    conflicting = _canonical_record(output_asset_id="other-output-asset")
    assert store._create_or_confirm_v1(record)[0] == "ATTESTED"

    result, persisted = store._create_or_confirm_v1(conflicting)

    assert result == "CONFLICT"
    assert persisted is None
    assert store._replay_post_cas_attestation_exact_v1(record.values[3]) == record


def test_concurrent_exact_replay_and_conflict_preserve_one_canonical_row(tmp_path: Path) -> None:
    """SQLite serialization permits replay but never replaces the canonical immutable row."""

    store = _construct_r25_attestation_store_v1(_repository(tmp_path))
    canonical = _canonical_record()
    conflicting = _canonical_record(output_asset_id="other-output-asset")
    assert store._create_or_confirm_v1(canonical) == ("ATTESTED", canonical)

    with ThreadPoolExecutor(max_workers=2) as executor:
        replay, conflict = tuple(
            executor.map(store._create_or_confirm_v1, (canonical, conflicting))
        )

    assert replay == ("ATTESTED_REPLAY", canonical)
    assert conflict == ("CONFLICT", None)
    assert store._replay_post_cas_attestation_exact_v1(canonical.values[3]) == canonical
    connection = sqlite3.connect(store._database_path)
    try:
        assert connection.execute("SELECT COUNT(*) FROM post_cas_application_attestations").fetchone() == (1,)
    finally:
        connection.close()


def test_corrupt_row_fails_closed_for_create_and_readonly_replay(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    store = _construct_r25_attestation_store_v1(repository)
    record = _canonical_record()
    assert store._create_or_confirm_v1(record)[0] == "ATTESTED"
    connection = sqlite3.connect(store._database_path)
    try:
        connection.execute(
            "UPDATE post_cas_application_attestations SET record_digest = ?",
            ("0" * 64,),
        )
        connection.commit()
    finally:
        connection.close()

    reopened = _construct_r25_attestation_store_v1(repository)
    assert reopened._create_or_confirm_v1(record) == ("CORRUPT", None)
    with pytest.raises(ValueError, match="CORRUPT"):
        reopened._replay_post_cas_attestation_exact_v1(record.values[3])


def test_private_service_consumes_one_trusted_record_before_create_or_confirm(tmp_path: Path) -> None:
    store = _construct_r25_attestation_store_v1(_repository(tmp_path))
    service = _construct_r25_materialization_service_v1(store)
    record = _canonical_record()
    request = service._issue_for_trusted_record_v1(record)

    assert service._materialize_v1(request) == ("ATTESTED", record)
    replay_request = service._issue_for_trusted_record_v1(record)
    assert service._materialize_v1(replay_request) == ("ATTESTED_REPLAY", record)
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        service._materialize_v1(request)


def test_private_service_rejects_direct_or_unregistered_requests(tmp_path: Path) -> None:
    service = _construct_r25_materialization_service_v1(
        _construct_r25_attestation_store_v1(_repository(tmp_path))
    )
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        _R25MaterializationServiceV1()
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        _R25MaterializationRequestV1()
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        _construct_r25_materialization_service_v1(object())
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        service._issue_for_trusted_record_v1(object())
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        service._materialize_v1(object())
