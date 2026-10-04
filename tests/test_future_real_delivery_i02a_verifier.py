"""Focused adversarial contracts for the private RFC-01 I02a verifier."""

from __future__ import annotations

import hashlib
import os
import sqlite3
import zlib
from dataclasses import replace
from pathlib import Path

import pytest

from manga_director.production import future_real_delivery_i02a_protocol as protocol
from manga_director.production import future_real_delivery_i02a_verifier as verifier_module
from manga_director.production.next_generation_local_durable_asset_owner import (
    LocalDurableAssetOwner,
    OwnerRegistrationMaterial,
)


def _chunk(chunk_type: bytes, data: bytes = b"") -> bytes:
    return (
        len(data).to_bytes(4, "big")
        + chunk_type
        + data
        + (zlib.crc32(chunk_type + data) & 0xFFFFFFFF).to_bytes(4, "big")
    )


def _png() -> bytes:
    header = (1).to_bytes(4, "big") + (1).to_bytes(4, "big") + bytes((8, 2, 0, 0, 0))
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", header) + _chunk(b"IDAT", b"x") + _chunk(b"IEND")


class _TestJournal(protocol._RealDeliveryJournalPeerV1):
    def __init__(self, facts: protocol._RegisteredAssetReplayFactsV1, callback: object = None) -> None:
        self._facts = facts
        self._callback = callback or protocol._JournalCompletionCallbackResultV1.COMMITTED
        self.peer: object | None = None
        self.received: object | None = None
        self.received_facts: tuple[object, object] | None = None

    def _bind_registered_owner_verification_peer_v1(self, peer: object, binding: object) -> None:
        if self.peer is not None:
            raise ValueError("rebind")
        self.peer = peer

    def _replay_registered_asset_for_owner_verification_v1(self) -> protocol._RegisteredAssetReplayFactsV1:
        return self._facts

    def _complete_registered_asset_from_verified_capability_v1(
        self, dispatch: object
    ) -> protocol._JournalCompletionCallbackResultV1:
        if not isinstance(dispatch, protocol._ActiveCompletionDispatchV1) or self.peer is None:
            raise ValueError("dispatch")
        self.received = dispatch
        self.received_facts = self.peer._assert_active_completion_dispatch_v1(dispatch)  # type: ignore[union-attr]
        if isinstance(self._callback, Exception):
            raise self._callback
        if callable(self._callback):
            return self._callback(dispatch)
        return self._callback  # type: ignore[return-value]


def _registered_owner(tmp_path: Path) -> tuple[LocalDurableAssetOwner, tuple[str, str, str, str, str, str]]:
    owner = LocalDurableAssetOwner(tmp_path / "owner")
    result = owner.register(
        OwnerRegistrationMaterial(
            attempt_id="attempt:i02a:001",
            provider_reference="provider:fake",
            image_bytes=_png(),
        )
    )
    assert result.outcome == "registered"
    with sqlite3.connect(tmp_path / "owner" / "registry" / "asset-owner.sqlite3") as connection:
        row = connection.execute(
            "SELECT asset_id, attempt_id, provider_reference, media_type, digest, storage_name "
            "FROM asset_registry"
        ).fetchone()
    assert row is not None
    return owner, tuple(str(value) for value in row)


def _facts(row: tuple[str, str, str, str, str, str]) -> protocol._RegisteredAssetReplayFactsV1:
    record = verifier_module._OwnerRegistryRecordV1(*row)
    return protocol._RegisteredAssetReplayFactsV1(
        delivery_identity="delivery:001",
        attempt_id=record.attempt_id,
        binding_digest="b" * 64,
        provider_reference=record.provider_reference,
        canonical_result_identity="c" * 64,
        logical_output_id="output:001",
        asset_id=record.asset_id,
        asset_registration_digest=verifier_module._asset_registration_digest(record),
        sha256=record.digest,
        expected_byte_length=len(_png()),
        media_type="image/png",
        provenance_assurance="UNVERIFIED",
        phase="ASSET_REGISTERED",
        sequence=1,
        last_event_digest="f" * 64,
    )


def _verifier_pair(
    tmp_path: Path,
    facts: protocol._RegisteredAssetReplayFactsV1 | None = None,
    callback: object = None,
) -> tuple[
    PrivateRegisteredOwnerAssetVerifierV1,
    _TestJournal,
    protocol._RegisteredOwnerVerificationJournalPeerV1,
    protocol._RegisteredOwnerVerificationVerifierPeerV1,
]:
    owner, row = _registered_owner(tmp_path)
    return _verifier_pair_for_owner(owner, facts or _facts(row), callback)


def _verifier_pair_for_owner(
    owner: LocalDurableAssetOwner,
    facts: protocol._RegisteredAssetReplayFactsV1,
    callback: object = None,
) -> tuple[
    PrivateRegisteredOwnerAssetVerifierV1,
    _TestJournal,
    protocol._RegisteredOwnerVerificationJournalPeerV1,
    protocol._RegisteredOwnerVerificationVerifierPeerV1,
]:
    journal = _TestJournal(facts, callback)
    state = protocol._create_isolated_test_protocol_state_v1()
    authority = state.issue_test_authority(_TestJournal)
    journal_peer, verifier_peer = state.create_pair(journal, authority)
    return PrivateRegisteredOwnerAssetVerifierV1(owner, verifier_peer), journal, journal_peer, verifier_peer


PrivateRegisteredOwnerAssetVerifierV1 = verifier_module.PrivateRegisteredOwnerAssetVerifierV1


@pytest.mark.skipif(__import__("os").name != "nt", reason="R05 frozen lease semantics are Windows-only")
def test_valid_registered_owner_asset_issues_one_completion_and_releases_after_callback(tmp_path: Path) -> None:
    verifier, journal, journal_peer, verifier_peer = _verifier_pair(tmp_path)
    request = journal_peer._issue_registered_owner_verification_request_v1()

    completion = verifier.verify(request)

    assert verifier_peer._consume_completion_and_call_journal_v1(completion) is protocol._JournalCompletionCallbackResultV1.COMMITTED
    assert isinstance(journal.received, protocol._ActiveCompletionDispatchV1)
    assert completion._verified.owner_attempt_id == "attempt:i02a:001"
    assert completion._verified.owner_storage_name.endswith(".png")
    assert completion._verified._release_leases is not None


@pytest.mark.skipif(__import__("os").name != "nt", reason="R05 frozen lease semantics are Windows-only")
@pytest.mark.parametrize("field", ("asset_id", "attempt_id", "provider_reference", "media_type", "sha256", "expected_byte_length", "asset_registration_digest"))
def test_owner_and_delivery_mismatches_fail_closed(tmp_path: Path, field: str) -> None:
    owner, row = _registered_owner(tmp_path / field)
    facts = _facts(row)
    replacements: dict[str, object] = {
        "asset_id": "asset:wrong",
        "attempt_id": "attempt:wrong",
        "provider_reference": "provider:wrong",
        "media_type": "image/jpeg",
        "sha256": "a" * 64,
        "expected_byte_length": len(_png()) + 1,
        "asset_registration_digest": "d" * 64,
    }
    verifier, _, journal_peer, _ = _verifier_pair_for_owner(
        owner, replace(facts, **{field: replacements[field]})
    )
    request = journal_peer._issue_registered_owner_verification_request_v1()

    with pytest.raises(ValueError, match="unavailable"):
        verifier.verify(request)


@pytest.mark.skipif(__import__("os").name != "nt", reason="R05 frozen lease semantics are Windows-only")
def test_invalid_registry_schema_missing_row_and_corrupt_png_issue_no_completion(tmp_path: Path) -> None:
    verifier, _, journal_peer, _ = _verifier_pair(tmp_path / "schema")
    request = journal_peer._issue_registered_owner_verification_request_v1()
    registry = tmp_path / "schema" / "owner" / "registry" / "asset-owner.sqlite3"
    with sqlite3.connect(registry) as connection:
        connection.execute("CREATE TABLE extra (value TEXT)")
    with pytest.raises(ValueError, match="unavailable"):
        verifier.verify(request)

    verifier, _, journal_peer, _ = _verifier_pair(tmp_path / "missing")
    request = journal_peer._issue_registered_owner_verification_request_v1()
    with sqlite3.connect(tmp_path / "missing" / "owner" / "registry" / "asset-owner.sqlite3") as connection:
        connection.execute("DELETE FROM asset_registry")
    with pytest.raises(ValueError, match="unavailable"):
        verifier.verify(request)

    verifier, _, journal_peer, _ = _verifier_pair(tmp_path / "png")
    request = journal_peer._issue_registered_owner_verification_request_v1()
    asset = next((tmp_path / "png" / "owner" / "assets").glob("*.png"))
    asset.write_bytes(b"\x89PNG\r\n\x1a\nnot-a-structure")
    with pytest.raises(ValueError, match="unavailable"):
        verifier.verify(request)


@pytest.mark.skipif(os.name != "nt", reason="R05 frozen lease semantics are Windows-only")
def test_busy_registry_and_containment_rejection_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    owner, row = _registered_owner(tmp_path / "busy")
    verifier, _, journal_peer, _ = _verifier_pair_for_owner(owner, _facts(row))
    registry = tmp_path / "busy" / "owner" / "registry" / "asset-owner.sqlite3"
    with sqlite3.connect(registry, timeout=0.0) as connection:
        connection.execute("BEGIN EXCLUSIVE")
        with pytest.raises(ValueError, match="unavailable"):
            verifier.verify(journal_peer._issue_registered_owner_verification_request_v1())

    owner, row = _registered_owner(tmp_path / "containment")
    verifier, _, journal_peer, _ = _verifier_pair_for_owner(owner, _facts(row))
    monkeypatch.setattr(verifier_module, "_is_strict_descendant", lambda _path, _root: False)
    with pytest.raises(ValueError, match="unavailable"):
        verifier.verify(journal_peer._issue_registered_owner_verification_request_v1())


@pytest.mark.skipif(os.name != "nt", reason="R05 frozen lease semantics are Windows-only")
def test_reparse_asset_path_fails_closed_when_windows_allows_test_symlink(tmp_path: Path) -> None:
    owner, row = _registered_owner(tmp_path)
    facts = _facts(row)
    asset = next((tmp_path / "owner" / "assets").glob("*.png"))
    outside = tmp_path / "outside.png"
    outside.write_bytes(_png())
    asset.unlink()
    try:
        os.symlink(outside, asset)
    except OSError as error:
        pytest.skip(f"symlink privilege unavailable: {error}")
    verifier, _, journal_peer, _ = _verifier_pair_for_owner(owner, facts)
    with pytest.raises(ValueError, match="unavailable"):
        verifier.verify(journal_peer._issue_registered_owner_verification_request_v1())


@pytest.mark.skipif(__import__("os").name != "nt", reason="R05 frozen lease semantics are Windows-only")
def test_forged_reused_and_cross_pair_requests_fail_closed(tmp_path: Path) -> None:
    verifier, _, journal_peer, _ = _verifier_pair(tmp_path / "one")
    request = journal_peer._issue_registered_owner_verification_request_v1()
    completion = verifier.verify(request)
    with pytest.raises(ValueError, match="unavailable"):
        verifier.verify(request)

    other_verifier, _, _, _ = _verifier_pair(tmp_path / "two")
    with pytest.raises(ValueError, match="unavailable"):
        other_verifier.verify(request)
    forged = object.__new__(protocol._RegisteredOwnerVerificationRequestV1)
    object.__setattr__(forged, "_pair_nonce", request._pair_nonce)
    object.__setattr__(forged, "_nonce", request._nonce)
    object.__setattr__(forged, "_facts", request.facts)
    with pytest.raises(ValueError, match="unavailable"):
        other_verifier.verify(forged)
    assert completion._verified.verified_sha256 == hashlib.sha256(_png()).hexdigest()


@pytest.mark.skipif(__import__("os").name != "nt", reason="R05 frozen lease semantics are Windows-only")
def test_callback_exception_before_commit_maps_not_committed_and_closes_leases(tmp_path: Path) -> None:
    verifier, _, journal_peer, verifier_peer = _verifier_pair(tmp_path, callback=RuntimeError("lost"))
    completion = verifier.verify(journal_peer._issue_registered_owner_verification_request_v1())

    assert verifier_peer._consume_completion_and_call_journal_v1(completion) is protocol._JournalCompletionCallbackResultV1.NOT_COMMITTED
    assert completion._verified._release_leases is not None
    with pytest.raises(ValueError):
        verifier_peer._consume_completion_and_call_journal_v1(completion)


@pytest.mark.skipif(__import__("os").name != "nt", reason="R05 frozen lease semantics are Windows-only")
def test_storage_name_path_derivation_root_drift_and_file_replacement_fail_closed(tmp_path: Path) -> None:
    owner, row = _registered_owner(tmp_path / "storage")
    facts = _facts(row)
    registry = tmp_path / "storage" / "owner" / "registry" / "asset-owner.sqlite3"
    with sqlite3.connect(registry) as connection:
        connection.execute("UPDATE asset_registry SET storage_name = ?", ("0" * 32 + ".png",))
    verifier, _, journal_peer, _ = _verifier_pair_for_owner(owner, facts)
    with pytest.raises(ValueError, match="unavailable"):
        verifier.verify(journal_peer._issue_registered_owner_verification_request_v1())

    owner, row = _registered_owner(tmp_path / "drift")
    facts = _facts(row)
    captured = owner._assets_root_identity
    assert captured is not None
    object.__setattr__(owner, "_assets_root_identity", replace(captured, file_index=captured.file_index + 1))
    verifier, _, journal_peer, _ = _verifier_pair_for_owner(owner, facts)
    with pytest.raises(ValueError, match="unavailable"):
        verifier.verify(journal_peer._issue_registered_owner_verification_request_v1())

    owner, row = _registered_owner(tmp_path / "replacement")
    facts = _facts(row)
    asset = next((tmp_path / "replacement" / "owner" / "assets").glob("*.png"))
    asset.write_bytes(_png() + b"replacement")
    verifier, _, journal_peer, _ = _verifier_pair_for_owner(owner, facts)
    with pytest.raises(ValueError, match="unavailable"):
        verifier.verify(journal_peer._issue_registered_owner_verification_request_v1())


@pytest.mark.skipif(__import__("os").name != "nt", reason="R05 frozen lease semantics are Windows-only")
def test_verifier_is_read_only_and_leases_are_live_during_callback_then_released(tmp_path: Path) -> None:
    owner, row = _registered_owner(tmp_path)
    facts = _facts(row)
    registry = tmp_path / "owner" / "registry" / "asset-owner.sqlite3"
    before = registry.read_bytes()
    observations: list[bool] = []

    def callback(dispatch: object) -> protocol._JournalCompletionCallbackResultV1:
        assert isinstance(dispatch, protocol._ActiveCompletionDispatchV1)
        assert journal.received_facts is not None
        release = journal.received_facts[1]._release_leases
        assert release is not None
        record = release.__self__
        observations.append(not record._released)
        return protocol._JournalCompletionCallbackResultV1.COMMITTED

    verifier, journal, journal_peer, verifier_peer = _verifier_pair_for_owner(owner, facts, callback)
    completion = verifier.verify(journal_peer._issue_registered_owner_verification_request_v1())
    assert registry.read_bytes() == before

    assert verifier_peer._consume_completion_and_call_journal_v1(completion) is protocol._JournalCompletionCallbackResultV1.COMMITTED
    assert observations == [True]
    release = completion._verified._release_leases
    assert release is not None
    assert release.__self__._released is True
    assert registry.read_bytes() == before


@pytest.mark.skipif(__import__("os").name != "nt", reason="R05 frozen lease semantics are Windows-only")
def test_final_file_lease_rejects_callback_time_replacement(tmp_path: Path) -> None:
    owner, row = _registered_owner(tmp_path)
    facts = _facts(row)
    replacement_attempts: list[bool] = []

    def callback(dispatch: object) -> protocol._JournalCompletionCallbackResultV1:
        assert isinstance(dispatch, protocol._ActiveCompletionDispatchV1)
        assert journal.received_facts is not None
        final_path = Path(journal.received_facts[1].final_file_identity[0])
        with pytest.raises(OSError):
            final_path.write_bytes(b"replacement")
        replacement_attempts.append(True)
        return protocol._JournalCompletionCallbackResultV1.COMMITTED

    verifier, journal, journal_peer, verifier_peer = _verifier_pair_for_owner(owner, facts, callback)
    completion = verifier.verify(journal_peer._issue_registered_owner_verification_request_v1())
    assert verifier_peer._consume_completion_and_call_journal_v1(completion) is protocol._JournalCompletionCallbackResultV1.COMMITTED
    assert replacement_attempts == [True]


def test_path_derivation_rejects_traversal_and_verifier_has_no_public_export(tmp_path: Path) -> None:
    owner = LocalDurableAssetOwner(tmp_path / "owner")
    with pytest.raises(ValueError, match="unavailable"):
        verifier_module._derive_final_asset_path(owner, "..\\escape.png")
