"""Focused adversarial contracts for the private RFC-01 I02 delivery journal."""

from __future__ import annotations

import hashlib
import sqlite3
import threading
from collections.abc import Callable
from pathlib import Path

import pytest

from manga_director.production import (
    future_real_delivery_i02_real_asset_delivery_journal as journal_module,
)
from manga_director.production import future_real_delivery_i02a_protocol as protocol
from manga_director.production.next_generation_asset_registration import (
    AssetRegistrationRuntimeResult,
)
from manga_director.production.next_generation_local_durable_asset_owner import (
    LocalDurableAssetOwner,
    OwnerRegistrationMaterial,
)

_IMAGE_BYTES = b"\x89PNG\r\n\x1a\n" + b"x" * 115
_IMAGE_DIGEST = hashlib.sha256(_IMAGE_BYTES).hexdigest()


def _owner(tmp_path: Path) -> LocalDurableAssetOwner:
    return LocalDurableAssetOwner(tmp_path / "owner")


def _binding(*, attempt_id: str = "attempt:001", digest: str = _IMAGE_DIGEST) -> journal_module._DeliveryBindingInputV1:
    canonical = journal_module._canonical_result_identity_v1(
        attempt_id=attempt_id,
        project_id="project:001",
        page_id="page:001",
        target_page_reference="target:001",
        provider_reference="provider:001",
        dispatch_identity="dispatch:001",
        idempotency_identity="idempotency:001",
        submission_receipt_identity="receipt:001",
        logical_output_id="output:001",
        asset_sha256=digest,
        expected_byte_length=123,
    )
    return journal_module._DeliveryBindingInputV1(
        attempt_id=attempt_id,
        project_id="project:001",
        page_id="page:001",
        target_page_reference="target:001",
        provider_reference="provider:001",
        dispatch_identity="dispatch:001",
        idempotency_identity="idempotency:001",
        submission_receipt_identity="receipt:001",
        logical_output_id="output:001",
        canonical_result_identity=canonical,
        asset_sha256=digest,
        expected_byte_length=123,
    )


def _journal(tmp_path: Path) -> journal_module.PrivateRealAssetDeliveryJournal:
    return journal_module.PrivateRealAssetDeliveryJournal(_owner(tmp_path))


def _asset_registered(journal: journal_module.PrivateRealAssetDeliveryJournal) -> journal_module._DeliveryReplayV1:
    binding = _binding()
    journal._begin_delivery_v1(binding)
    journal._record_bytes_validated_v1(123, binding.asset_sha256, "image/png")
    result = journal._owner.register(
        OwnerRegistrationMaterial(
            attempt_id=binding.attempt_id,
            provider_reference=binding.provider_reference,
            image_bytes=_IMAGE_BYTES,
        )
    )
    assert result.outcome == "registered"
    return journal._record_authenticated_asset_registered_v1(result)


def _pair(
    journal: journal_module.PrivateRealAssetDeliveryJournal,
) -> tuple[protocol._ProtocolStateV1, protocol._RegisteredOwnerVerificationJournalPeerV1, protocol._RegisteredOwnerVerificationVerifierPeerV1]:
    state = protocol._create_isolated_test_protocol_state_v1()
    channel = state.take_bootstrap()
    channel._register_production_journal_class_once_v1(journal_module.PrivateRealAssetDeliveryJournal)
    journal_peer, verifier_peer = state.create_pair(journal)
    return state, journal_peer, verifier_peer


def _verified(*, sha256: str = _IMAGE_DIGEST, length: int = 123) -> protocol._VerifiedOwnerAssetFactsV1:
    return protocol._VerifiedOwnerAssetFactsV1(
        assets_root_identity=("assets", 1, 2),
        final_file_identity=("asset.png", 1, 3, length),
        verified_sha256=sha256,
        verified_byte_length=length,
        verified_media_type="image/png",
        owner_attempt_id="attempt:001",
        owner_provider_reference="provider:001",
        owner_digest=sha256,
        owner_storage_name="a" * 32 + ".png",
    )


def test_exact_owner_location_schema_and_reopen_are_deterministic(tmp_path: Path) -> None:
    owner = _owner(tmp_path)
    journal = journal_module.PrivateRealAssetDeliveryJournal(owner)
    expected = owner._root / "_durability" / "_post_lts_real_asset_delivery" / "real-asset-delivery.sqlite3"
    assert journal._database_path == expected
    assert expected.is_file()
    reopened = journal_module.PrivateRealAssetDeliveryJournal(owner)
    with pytest.raises(ValueError):
        reopened._replay_v1()


def test_zero_byte_existing_database_and_nonempty_new_owner_directory_fail_closed(tmp_path: Path) -> None:
    owner = _owner(tmp_path)
    database = owner._root / "_durability" / "_post_lts_real_asset_delivery" / "real-asset-delivery.sqlite3"
    database.parent.mkdir(parents=True)
    database.touch()
    with pytest.raises(ValueError):
        journal_module.PrivateRealAssetDeliveryJournal(owner)
    second_owner = _owner(tmp_path / "second")
    directory = second_owner._root / "_durability" / "_post_lts_real_asset_delivery"
    directory.mkdir(parents=True)
    (directory / "unknown.txt").write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        journal_module.PrivateRealAssetDeliveryJournal(second_owner)


def test_partial_existing_database_fails_closed_without_recreation(tmp_path: Path) -> None:
    owner = _owner(tmp_path)
    database = owner._root / "_durability" / "_post_lts_real_asset_delivery" / "real-asset-delivery.sqlite3"
    database.parent.mkdir(parents=True)
    database.write_bytes(b"not a sqlite database")
    with pytest.raises(ValueError):
        journal_module.PrivateRealAssetDeliveryJournal(owner)
    assert database.read_bytes() == b"not a sqlite database"


def test_binding_identity_event_chain_and_asset_registration_digest_replay(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    replay = _asset_registered(journal)
    assert replay.status is journal_module._DeliveryStatusV1.ASSET_REGISTERED
    assert replay.sequence == 2
    assert replay.asset_registration_digest == journal_module._asset_registration_digest(
        replay.asset_id, "attempt:001", "provider:001", "image/png", _IMAGE_DIGEST
    )
    assert journal._replay_v1() == replay


def test_exact_duplicate_replays_and_different_attempt_binding_is_conflict(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    initial = journal._begin_delivery_v1(_binding())
    assert journal._begin_delivery_v1(_binding()) == initial
    conflict = journal._begin_delivery_v1(_binding(digest="c" * 64))
    assert conflict.status is journal_module._DeliveryStatusV1.DELIVERY_CONFLICT


def test_arbitrary_canonical_identity_is_rejected_before_any_delivery_mutation() -> None:
    with pytest.raises(ValueError):
        journal_module._DeliveryBindingInputV1(
            attempt_id="attempt:001",
            project_id="project:001",
            page_id="page:001",
            target_page_reference="target:001",
            provider_reference="provider:001",
            dispatch_identity="dispatch:001",
            idempotency_identity="idempotency:001",
            submission_receipt_identity="receipt:001",
            logical_output_id="output:001",
            canonical_result_identity="b" * 64,
            asset_sha256=_IMAGE_DIGEST,
            expected_byte_length=123,
        )


def test_bytes_validated_reopen_is_read_only_recovery_required(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    binding = _binding()
    journal._begin_delivery_v1(binding)
    journal._record_bytes_validated_v1(123, binding.asset_sha256, "image/png")
    reopened = journal_module.PrivateRealAssetDeliveryJournal(journal._owner)
    projection = reopened._reopen_v1(binding.delivery_identity)
    assert projection.status is journal_module._DeliveryStatusV1.RECOVERY_REQUIRED
    assert reopened._replay_v1(binding.delivery_identity).status is journal_module._DeliveryStatusV1.BYTES_VALIDATED


def test_raw_owner_like_facts_cannot_create_asset_registered(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    binding = _binding()
    journal._begin_delivery_v1(binding)
    journal._record_bytes_validated_v1(123, binding.asset_sha256, "image/png")
    with pytest.raises(ValueError):
        journal._record_asset_registered_v1(
            "asset:generated:forged",
            binding.attempt_id,
            binding.provider_reference,
            "image/png",
            binding.asset_sha256,
        )
    assert journal._replay_v1().status is journal_module._DeliveryStatusV1.BYTES_VALIDATED


@pytest.mark.parametrize("variant", ("forged", "copied", "foreign", "consumed"))
def test_r14_case_08_unauthenticated_registration_result_is_recovery_required(
    tmp_path: Path, variant: str
) -> None:
    journal = _journal(tmp_path)
    binding = _binding()
    journal._begin_delivery_v1(binding)
    journal._record_bytes_validated_v1(123, binding.asset_sha256, "image/png")
    result = journal._owner.register(
        OwnerRegistrationMaterial(
            attempt_id=binding.attempt_id,
            provider_reference=binding.provider_reference,
            image_bytes=_IMAGE_BYTES,
        )
    )
    if variant == "forged":
        candidate: object = AssetRegistrationRuntimeResult(
            binding.attempt_id, binding.provider_reference, "registered"
        )
    elif variant == "copied":
        candidate = AssetRegistrationRuntimeResult(
            result.attempt_id, result.provider_reference, result.outcome, result.output,
            result.durable_registration_confirmed,
        )
    elif variant == "foreign":
        foreign = _owner(tmp_path / "foreign")
        candidate = foreign.register(
            OwnerRegistrationMaterial(binding.attempt_id, binding.provider_reference, _IMAGE_BYTES)
        )
    else:
        journal._owner._consume_real_delivery_registration_v1(result)
        candidate = result
    recovery = journal._record_authenticated_asset_registered_v1(candidate)
    assert recovery.status is journal_module._DeliveryStatusV1.RECOVERY_REQUIRED
    assert journal._replay_v1().status is journal_module._DeliveryStatusV1.BYTES_VALIDATED
    assert journal._replay_v1().sequence == 1


def test_r14_case_14_precommit_failure_keeps_consumed_authority_dead(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal = _journal(tmp_path)
    binding = _binding()
    journal._begin_delivery_v1(binding)
    journal._record_bytes_validated_v1(123, binding.asset_sha256, "image/png")
    result = journal._owner.register(
        OwnerRegistrationMaterial(binding.attempt_id, binding.provider_reference, _IMAGE_BYTES)
    )

    def fail_precommit(*args: object, **kwargs: object) -> object:
        raise ValueError(journal_module._UNAVAILABLE)

    monkeypatch.setattr(journal_module.PrivateRealAssetDeliveryJournal, "_append_event_v1", fail_precommit)
    recovery = journal._record_authenticated_asset_registered_v1(result)
    assert recovery.status is journal_module._DeliveryStatusV1.RECOVERY_REQUIRED
    assert journal._replay_v1().status is journal_module._DeliveryStatusV1.BYTES_VALIDATED
    assert journal._replay_v1().sequence == 1
    assert journal._record_authenticated_asset_registered_v1(result).status is journal_module._DeliveryStatusV1.RECOVERY_REQUIRED


def test_r14_case_11_commit_failure_leaves_no_owner_or_i02_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = _owner(tmp_path)

    def fail_owner_commit(*args: object, **kwargs: object) -> object:
        raise RuntimeError("synthetic owner commit failure")

    monkeypatch.setattr(LocalDurableAssetOwner, "_commit_registration", fail_owner_commit)
    result = owner.register(OwnerRegistrationMaterial("attempt:001", "provider:001", _IMAGE_BYTES))

    assert result.outcome == "failed"
    assert result.durable_registration_confirmed is False
    with sqlite3.connect(owner._registry_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM asset_registry").fetchone()[0] == 0
    assert tuple((owner._root / "assets").glob("*.png")) == ()


def test_r14_case_13_post_commit_commitment_allocation_failure_is_not_reissued(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class RejectingCommitments(dict[int, object]):
        def __setitem__(self, key: int, value: object) -> None:
            raise RuntimeError("synthetic commitment allocation failure")

    owner = _owner(tmp_path)
    owner._live_registration_commitments_by_result_id = RejectingCommitments()
    initial = owner.register(OwnerRegistrationMaterial("attempt:001", "provider:001", _IMAGE_BYTES))
    replayed = owner.register(OwnerRegistrationMaterial("attempt:001", "provider:001", _IMAGE_BYTES))

    assert initial.outcome == "failed"
    assert replayed.outcome == "registered"
    assert replayed.durable_registration_confirmed is True
    journal = journal_module.PrivateRealAssetDeliveryJournal(owner)
    binding = _binding()
    journal._begin_delivery_v1(binding)
    journal._record_bytes_validated_v1(123, binding.asset_sha256, "image/png")
    assert journal._record_authenticated_asset_registered_v1(replayed).status is journal_module._DeliveryStatusV1.RECOVERY_REQUIRED
    assert journal._replay_v1().sequence == 1


def test_r14_case_16_restart_before_asset_registration_remains_recovery_required(tmp_path: Path) -> None:
    owner = _owner(tmp_path)
    journal = journal_module.PrivateRealAssetDeliveryJournal(owner)
    binding = _binding()
    journal._begin_delivery_v1(binding)
    journal._record_bytes_validated_v1(123, binding.asset_sha256, "image/png")
    result = owner.register(OwnerRegistrationMaterial(binding.attempt_id, binding.provider_reference, _IMAGE_BYTES))
    restarted_owner = LocalDurableAssetOwner(owner._root)
    restarted = journal_module.PrivateRealAssetDeliveryJournal(restarted_owner)

    assert restarted._reopen_v1(binding.delivery_identity).status is journal_module._DeliveryStatusV1.RECOVERY_REQUIRED
    assert restarted._begin_delivery_v1(binding).status is journal_module._DeliveryStatusV1.BYTES_VALIDATED
    assert restarted._record_authenticated_asset_registered_v1(result).status is journal_module._DeliveryStatusV1.RECOVERY_REQUIRED
    assert restarted._replay_v1(binding.delivery_identity).sequence == 1


def test_r14_case_07_postcommit_ack_loss_is_unknown_with_one_durable_completion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal = _journal(tmp_path)
    _asset_registered(journal)
    _, journal_peer, verifier_peer = _pair(journal)
    completion = verifier_peer._consume_request_and_issue_completion_v1(journal_peer._issue_registered_owner_verification_request_v1(), _verified())
    original = journal_module.PrivateRealAssetDeliveryJournal._complete_registered_asset_from_verified_capability_v1

    def commit_then_lose(
        self: journal_module.PrivateRealAssetDeliveryJournal, dispatch: protocol._ActiveCompletionDispatchV1
    ) -> protocol._JournalCompletionCallbackResultV1:
        assert original(self, dispatch) is protocol._JournalCompletionCallbackResultV1.COMMITTED
        raise RuntimeError("acknowledgement lost")

    monkeypatch.setattr(journal_module.PrivateRealAssetDeliveryJournal, "_complete_registered_asset_from_verified_capability_v1", commit_then_lose)
    assert verifier_peer._consume_completion_and_call_journal_v1(completion) is protocol._JournalCompletionCallbackResultV1.UNKNOWN_OUTCOME
    assert journal._replay_v1().status is journal_module._DeliveryStatusV1.DELIVERY_COMPLETED
    assert journal._replay_v1().sequence == 3
    with pytest.raises(ValueError):
        verifier_peer._consume_completion_and_call_journal_v1(completion)


def test_owner_registry_tamper_is_classified_corrupt_without_an_i02_event(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    binding = _binding()
    journal._begin_delivery_v1(binding)
    journal._record_bytes_validated_v1(123, binding.asset_sha256, "image/png")
    result = journal._owner.register(
        OwnerRegistrationMaterial(
            attempt_id=binding.attempt_id,
            provider_reference=binding.provider_reference,
            image_bytes=_IMAGE_BYTES,
        )
    )
    with sqlite3.connect(journal._owner._registry_path) as connection:
        connection.execute("UPDATE asset_registry SET digest = ?", ("0" * 64,))
    assert journal._record_authenticated_asset_registered_v1(result).status is journal_module._DeliveryStatusV1.CORRUPT
    assert journal._replay_v1().status is journal_module._DeliveryStatusV1.BYTES_VALIDATED


def test_event_and_state_tampering_fail_closed_on_replay(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    replay = _asset_registered(journal)
    connection = sqlite3.connect(journal._database_path)
    try:
        connection.execute(
            "UPDATE real_asset_delivery_events SET previous_event_digest = ? WHERE delivery_identity = ? AND sequence = 2",
            ("0" * 64, replay.binding.delivery_identity),
        )
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ValueError):
        journal._replay_v1()


@pytest.mark.parametrize(
    ("statement", "parameters"),
    (
        ("UPDATE real_asset_delivery_events SET payload_digest = ?", ("0" * 64,)),
        ("UPDATE real_asset_delivery_events SET event_digest = ?", ("0" * 64,)),
        ("UPDATE real_asset_delivery_events SET previous_event_digest = ? WHERE sequence = 1", ("0" * 64,)),
        ("UPDATE real_asset_delivery_bindings SET sequence = ?", (99,)),
        ("UPDATE real_asset_delivery_bindings SET phase = ?", ("DELIVERY_COMPLETED",)),
        ("UPDATE real_asset_delivery_bindings SET binding_digest = ?", ("0" * 64,)),
    ),
)
def test_r14_case_20_tampered_durable_reopen_is_read_only_corrupt(
    tmp_path: Path, statement: str, parameters: tuple[object, ...]
) -> None:
    journal = _journal(tmp_path)
    replay = _asset_registered(journal)
    before = journal._database_path.read_bytes()
    with sqlite3.connect(journal._database_path) as connection:
        event_count = connection.execute("SELECT COUNT(*) FROM real_asset_delivery_events").fetchone()[0]
    with sqlite3.connect(journal._database_path) as connection:
        connection.execute(statement, parameters)
    tampered = journal._database_path.read_bytes()
    assert tampered != before
    assert journal._reopen_v1(replay.binding.delivery_identity).status is journal_module._DeliveryStatusV1.CORRUPT
    with pytest.raises(ValueError):
        journal._begin_delivery_v1(replay.binding)
    assert journal._database_path.read_bytes() == tampered
    with sqlite3.connect(journal._database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM real_asset_delivery_events").fetchone()[0] == event_count


@pytest.mark.parametrize(
    "statement",
    (
        "PRAGMA user_version = 2",
        "CREATE TABLE r14_case_20_unexpected_object (value TEXT)",
    ),
)
def test_r14_case_20_schema_tampering_reopens_as_read_only_corrupt(tmp_path: Path, statement: str) -> None:
    journal = _journal(tmp_path)
    replay = _asset_registered(journal)
    with sqlite3.connect(journal._database_path) as connection:
        event_count = connection.execute("SELECT COUNT(*) FROM real_asset_delivery_events").fetchone()[0]
        connection.execute(statement)
    tampered = journal._database_path.read_bytes()
    assert journal._reopen_v1(replay.binding.delivery_identity).status is journal_module._DeliveryStatusV1.CORRUPT
    with pytest.raises(ValueError):
        journal._begin_delivery_v1(replay.binding)
    assert journal._database_path.read_bytes() == tampered
    with sqlite3.connect(journal._database_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM real_asset_delivery_events").fetchone()[0] == event_count


def test_r14_case_20_invalid_reopen_input_is_not_classified_as_corrupt(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    with pytest.raises(ValueError, match="unavailable"):
        journal._reopen_v1("invalid")
    with pytest.raises(ValueError, match="unavailable"):
        journal._reopen_v1("a" * 64)


def test_schema_extra_object_and_version_tampering_fail_closed(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    connection = sqlite3.connect(journal._database_path)
    try:
        connection.execute("CREATE TABLE unexpected_table (value TEXT)")
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ValueError):
        journal._replay_v1("a" * 64)


def test_i02a_request_and_exact_completion_callback_commit_once(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    replay = _asset_registered(journal)
    _, journal_peer, verifier_peer = _pair(journal)
    request = journal_peer._issue_registered_owner_verification_request_v1()
    assert request.facts.delivery_identity == replay.binding.delivery_identity
    completion = verifier_peer._consume_request_and_issue_completion_v1(request, _verified())
    assert verifier_peer._consume_completion_and_call_journal_v1(completion) is protocol._JournalCompletionCallbackResultV1.COMMITTED
    assert journal._replay_v1().status is journal_module._DeliveryStatusV1.DELIVERY_COMPLETED
    with pytest.raises(ValueError):
        verifier_peer._consume_completion_and_call_journal_v1(completion)


def test_completion_cross_binding_mismatch_never_appends_completion(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    _asset_registered(journal)
    _, journal_peer, verifier_peer = _pair(journal)
    request = journal_peer._issue_registered_owner_verification_request_v1()
    completion = verifier_peer._consume_request_and_issue_completion_v1(request, _verified(sha256="c" * 64))
    assert verifier_peer._consume_completion_and_call_journal_v1(completion) is protocol._JournalCompletionCallbackResultV1.CORRUPT
    assert journal._replay_v1().status is journal_module._DeliveryStatusV1.ASSET_REGISTERED


def test_completion_consumers_converge_to_one_event(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    _asset_registered(journal)
    _, journal_peer, verifier_peer = _pair(journal)
    request = journal_peer._issue_registered_owner_verification_request_v1()
    completion = verifier_peer._consume_request_and_issue_completion_v1(request, _verified())
    outcomes: list[object] = []

    def consume() -> None:
        try:
            outcomes.append(verifier_peer._consume_completion_and_call_journal_v1(completion))
        except ValueError:
            outcomes.append("REJECTED")

    threads = [threading.Thread(target=consume) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert outcomes.count(protocol._JournalCompletionCallbackResultV1.COMMITTED) == 1
    assert outcomes.count("REJECTED") == 1
    assert journal._replay_v1().sequence == 3


def test_protocol_request_requires_asset_registered_and_does_not_mutate_journal(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    binding = _binding()
    journal._begin_delivery_v1(binding)
    _, journal_peer, _ = _pair(journal)
    with pytest.raises(ValueError):
        journal_peer._issue_registered_owner_verification_request_v1()
    assert journal._replay_v1().status is journal_module._DeliveryStatusV1.DELIVERY_STARTED


def test_public_packages_do_not_export_i02() -> None:
    root_source = Path(__file__).parents[1] / "src" / "manga_director" / "__init__.py"
    production_source = root_source.parent / "production" / "__init__.py"
    assert "future_real_delivery_i02" not in root_source.read_text(encoding="utf-8")
    assert "future_real_delivery_i02" not in production_source.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("statement", "parameters"),
    [
        ("PRAGMA user_version = 2", ()),
        (
            "UPDATE real_asset_delivery_schema_meta SET schema_version = 2 "
            "WHERE schema_id = 'manga_director.real_asset_delivery_journal'",
            (),
        ),
        ("CREATE VIEW unexpected_view AS SELECT 1 AS value", ()),
        ("CREATE TRIGGER unexpected_trigger AFTER INSERT ON real_asset_delivery_events BEGIN SELECT 1; END", ()),
        ("CREATE INDEX unexpected_index ON real_asset_delivery_events (event_type)", ()),
    ],
)
def test_reopen_rejects_schema_version_metadata_and_object_tampering(
    tmp_path: Path, statement: str, parameters: tuple[object, ...]
) -> None:
    journal = _journal(tmp_path)
    connection = sqlite3.connect(journal._database_path)
    try:
        connection.execute(statement, parameters)
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ValueError):
        journal_module.PrivateRealAssetDeliveryJournal(_owner(tmp_path))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda connection, replay: connection.execute(
            "UPDATE real_asset_delivery_bindings SET binding_digest = ? WHERE delivery_identity = ?",
            ("c" * 64, replay.binding.delivery_identity),
        ),
        lambda connection, replay: connection.execute(
            "UPDATE real_asset_delivery_bindings SET phase = 'DELIVERY_COMPLETED' WHERE delivery_identity = ?",
            (replay.binding.delivery_identity,),
        ),
        lambda connection, replay: connection.execute(
            "UPDATE real_asset_delivery_events SET payload_digest = ? WHERE delivery_identity = ? AND sequence = 1",
            ("c" * 64, replay.binding.delivery_identity),
        ),
        lambda connection, replay: connection.execute(
            "UPDATE real_asset_delivery_events SET event_digest = ? WHERE delivery_identity = ? AND sequence = 1",
            ("c" * 64, replay.binding.delivery_identity),
        ),
        lambda connection, replay: connection.execute(
            "UPDATE real_asset_delivery_events SET sequence = 9 WHERE delivery_identity = ? AND sequence = 1",
            (replay.binding.delivery_identity,),
        ),
        lambda connection, replay: connection.execute(
            "UPDATE real_asset_delivery_events SET payload_json = ? WHERE delivery_identity = ? AND sequence = 2",
            ('{"asset_id":"asset:generated:001","asset_registration_digest":"' + "c" * 64 + '"}', replay.binding.delivery_identity),
        ),
    ],
)
def test_replay_rejects_binding_event_and_state_tampering(
    tmp_path: Path,
    mutate: Callable[[sqlite3.Connection, journal_module._DeliveryReplayV1], object],
) -> None:
    journal = _journal(tmp_path)
    replay = _asset_registered(journal)
    connection = sqlite3.connect(journal._database_path)
    try:
        mutate(connection, replay)
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ValueError):
        journal._replay_v1()


def test_malformed_bytes_are_terminal_and_reopen_is_deterministic(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    binding = _binding()
    journal._begin_delivery_v1(binding)
    malformed = journal._record_bytes_validated_v1(122, binding.asset_sha256, "image/png")
    assert malformed.status is journal_module._DeliveryStatusV1.DELIVERY_MALFORMED
    with pytest.raises(ValueError):
        journal._record_bytes_validated_v1(123, binding.asset_sha256, "image/png")
    reopened = journal_module.PrivateRealAssetDeliveryJournal(_owner(tmp_path))
    assert reopened._replay_v1(binding.delivery_identity) == malformed


def test_different_attempt_has_a_distinct_canonical_result_identity(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    initial = journal._begin_delivery_v1(_binding())
    second = journal._begin_delivery_v1(_binding(attempt_id="attempt:002"))
    assert second.status is journal_module._DeliveryStatusV1.DELIVERY_STARTED
    assert journal._replay_v1(initial.binding.delivery_identity) == initial


def test_reopened_exact_asset_registered_binding_can_issue_fresh_request_without_durable_mutation(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    initial = _asset_registered(journal)
    reopened = journal_module.PrivateRealAssetDeliveryJournal(_owner(tmp_path))
    assert reopened._begin_delivery_v1(initial.binding) == initial
    _, peer, _ = _pair(reopened)
    request = peer._issue_registered_owner_verification_request_v1()
    assert request.facts.last_event_digest == initial.last_event_digest
    assert reopened._replay_v1().sequence == 2


def test_cross_pair_completion_is_not_accepted_by_the_other_journal(tmp_path: Path) -> None:
    first = _journal(tmp_path / "first")
    second = _journal(tmp_path / "second")
    _asset_registered(first)
    _asset_registered(second)
    _, _, first_verifier = _pair(first)
    _, second_peer, second_verifier = _pair(second)
    request = second_peer._issue_registered_owner_verification_request_v1()
    completion = second_verifier._consume_request_and_issue_completion_v1(request, _verified())
    assert first._complete_registered_asset_from_verified_capability_v1(completion) is protocol._JournalCompletionCallbackResultV1.NOT_COMMITTED
    assert first._replay_v1().status is journal_module._DeliveryStatusV1.ASSET_REGISTERED
    assert first_verifier is not None


def test_event_count_and_event_size_bounds_fail_closed(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    binding = _binding()
    journal._begin_delivery_v1(binding)
    connection = sqlite3.connect(journal._database_path)
    try:
        with pytest.raises(ValueError):
            journal._insert_event(connection, binding, 1, "BYTES_VALIDATED", "0" * 64, {"x": "x" * (9 * 1024)})
    finally:
        connection.close()
    replay = journal._replay_v1()
    connection = sqlite3.connect(journal._database_path)
    try:
        connection.execute(
            "UPDATE real_asset_delivery_bindings SET sequence = 16 WHERE delivery_identity = ?",
            (replay.binding.delivery_identity,),
        )
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(ValueError):
        journal._replay_v1()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("delivery_identity", "c" * 64),
        ("attempt_id", "attempt:other"),
        ("binding_digest", "c" * 64),
        ("provider_reference", "provider:other"),
        ("canonical_result_identity", "c" * 64),
        ("logical_output_id", "output:other"),
        ("asset_id", "asset:other"),
        ("asset_registration_digest", "c" * 64),
        ("sha256", "c" * 64),
        ("expected_byte_length", 124),
        ("media_type", "image/jpeg"),
        ("sequence", 99),
        ("last_event_digest", "c" * 64),
    ],
)
def test_r12_rejects_each_request_fact_mismatch_without_completion(
    tmp_path: Path, field: str, value: object
) -> None:
    journal = _journal(tmp_path)
    _asset_registered(journal)
    _, journal_peer, verifier_peer = _pair(journal)
    request = journal_peer._issue_registered_owner_verification_request_v1()
    object.__setattr__(request.facts, field, value)
    completion = verifier_peer._consume_request_and_issue_completion_v1(request, _verified())
    assert verifier_peer._consume_completion_and_call_journal_v1(completion) is protocol._JournalCompletionCallbackResultV1.CORRUPT
    assert journal._replay_v1().status is journal_module._DeliveryStatusV1.ASSET_REGISTERED


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("owner_attempt_id", "attempt:other"),
        ("owner_provider_reference", "provider:other"),
        ("owner_digest", "c" * 64),
        ("verified_sha256", "c" * 64),
        ("verified_byte_length", 124),
        ("verified_media_type", "image/jpeg"),
    ],
)
def test_r12_rejects_each_verified_owner_fact_mismatch_without_completion(
    tmp_path: Path, field: str, value: object
) -> None:
    journal = _journal(tmp_path)
    _asset_registered(journal)
    _, journal_peer, verifier_peer = _pair(journal)
    request = journal_peer._issue_registered_owner_verification_request_v1()
    verified = _verified()
    object.__setattr__(verified, field, value)
    completion = verifier_peer._consume_request_and_issue_completion_v1(request, verified)
    assert verifier_peer._consume_completion_and_call_journal_v1(completion) is protocol._JournalCompletionCallbackResultV1.CORRUPT
    assert journal._replay_v1().status is journal_module._DeliveryStatusV1.ASSET_REGISTERED


def test_completion_replay_after_commit_is_idempotent_and_never_appends_another_event(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    _asset_registered(journal)
    _, journal_peer, verifier_peer = _pair(journal)
    request = journal_peer._issue_registered_owner_verification_request_v1()
    completion = verifier_peer._consume_request_and_issue_completion_v1(request, _verified())
    assert verifier_peer._consume_completion_and_call_journal_v1(completion) is protocol._JournalCompletionCallbackResultV1.COMMITTED
    with pytest.raises(ValueError):
        journal_peer._issue_registered_owner_verification_request_v1()
    assert journal._replay_v1().sequence == 3


def test_locked_store_fails_closed_without_repair(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    lock = sqlite3.connect(journal._database_path, timeout=0.0, isolation_level=None)
    try:
        lock.execute("BEGIN EXCLUSIVE")
        with pytest.raises(ValueError):
            journal._begin_delivery_v1(_binding())
    finally:
        lock.rollback()
        lock.close()
    assert journal._begin_delivery_v1(_binding()).status is journal_module._DeliveryStatusV1.DELIVERY_STARTED


def test_each_journal_operation_releases_its_sqlite_connection_deterministically(tmp_path: Path) -> None:
    journal = _journal(tmp_path)
    journal._begin_delivery_v1(_binding())
    journal._replay_v1()
    lock = sqlite3.connect(journal._database_path, timeout=0.0, isolation_level=None)
    try:
        lock.execute("BEGIN EXCLUSIVE")
    finally:
        lock.rollback()
        lock.close()
