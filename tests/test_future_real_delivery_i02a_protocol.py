"""Focused adversarial contracts for the private RFC-01 I02a protocol."""

from __future__ import annotations

import copy
import pickle
import threading
from dataclasses import replace

import pytest

from manga_director.production import future_real_delivery_i02a_protocol as protocol


def _facts() -> protocol._RegisteredAssetReplayFactsV1:
    return protocol._RegisteredAssetReplayFactsV1(
        delivery_identity="delivery:001", attempt_id="attempt:001", binding_digest="b" * 64,
        provider_reference="provider:001", canonical_result_identity="c" * 64,
        logical_output_id="output:001", asset_id="asset:001", asset_registration_digest="d" * 64,
        sha256="e" * 64, expected_byte_length=123, media_type="image/png",
        provenance_assurance="UNVERIFIED", phase="ASSET_REGISTERED", sequence=1,
        last_event_digest="f" * 64,
    )


class _TestJournal(protocol._RealDeliveryJournalPeerV1):
    def __init__(
        self,
        *,
        callback: object = protocol._JournalCompletionCallbackResultV1.COMMITTED,
        delivery_identity: str = "delivery:001",
    ) -> None:
        self.peer: object | None = None
        self.callback = callback
        self.callback_count = 0
        self.delivery_identity = delivery_identity

    def _bind_registered_owner_verification_peer_v1(self, peer: object, binding: object) -> None:
        if self.peer is not None:
            raise ValueError("rebind")
        self.peer = peer

    def _replay_registered_asset_for_owner_verification_v1(self) -> protocol._RegisteredAssetReplayFactsV1:
        return replace(_facts(), delivery_identity=self.delivery_identity)

    def _complete_registered_asset_from_verified_capability_v1(
        self, dispatch: object
    ) -> protocol._JournalCompletionCallbackResultV1:
        if not isinstance(dispatch, protocol._ActiveCompletionDispatchV1) or self.peer is None:
            raise ValueError("bad capability")
        self.peer._assert_active_completion_dispatch_v1(dispatch)  # type: ignore[union-attr]
        if isinstance(self.callback, Exception):
            raise self.callback
        self.callback_count += 1
        return self.callback  # type: ignore[return-value]


def _state_and_pair() -> tuple[
    protocol._ProtocolStateV1,
    _TestJournal,
    protocol._RegisteredOwnerVerificationJournalPeerV1,
    protocol._RegisteredOwnerVerificationVerifierPeerV1,
]:
    state = protocol._create_isolated_test_protocol_state_v1()
    journal = _TestJournal()
    authority = state.issue_test_authority(_TestJournal)
    journal_peer, verifier_peer = state.create_pair(journal, authority)
    return state, journal, journal_peer, verifier_peer


def _verified() -> protocol._VerifiedOwnerAssetFactsV1:
    return protocol._VerifiedOwnerAssetFactsV1(
        assets_root_identity=("assets", 1, 2), final_file_identity=("asset.png", 1, 3, 123),
        verified_sha256="e" * 64, verified_byte_length=123, verified_media_type="image/png",
    )


def test_capabilities_reject_direct_construction_subclass_copy_and_serialization() -> None:
    with pytest.raises(TypeError):
        protocol._RegisteredOwnerVerificationRequestV1()
    with pytest.raises(TypeError):
        protocol._RegisteredOwnerVerificationCompletionCapabilityV1()
    with pytest.raises(TypeError):
        type("Forged", (protocol._RegisteredOwnerVerificationRequestV1,), {})
    with pytest.raises(TypeError):
        type("ForgedCompletion", (protocol._RegisteredOwnerVerificationCompletionCapabilityV1,), {})
    _, _, journal_peer, _ = _state_and_pair()
    request = journal_peer._issue_registered_owner_verification_request_v1()
    with pytest.raises(TypeError):
        copy.copy(request)
    with pytest.raises(TypeError):
        pickle.dumps(request)


def test_pair_request_completion_are_exact_pair_bound_and_one_shot() -> None:
    _, _, journal_peer, verifier_peer = _state_and_pair()
    request = journal_peer._issue_registered_owner_verification_request_v1()
    completion = verifier_peer._consume_request_and_issue_completion_v1(request, _verified())
    assert verifier_peer._consume_completion_and_call_journal_v1(completion) is protocol._JournalCompletionCallbackResultV1.COMMITTED
    with pytest.raises(ValueError):
        verifier_peer._consume_completion_and_call_journal_v1(completion)
    with pytest.raises(ValueError):
        verifier_peer._consume_request_and_issue_completion_v1(request, _verified())


def test_forged_completion_preserves_the_legitimate_pending_record() -> None:
    state, journal, journal_peer, verifier_peer = _state_and_pair()
    request = journal_peer._issue_registered_owner_verification_request_v1()
    completion = verifier_peer._consume_request_and_issue_completion_v1(request, _verified())
    forged = object.__new__(protocol._RegisteredOwnerVerificationCompletionCapabilityV1)
    for field in ("_state", "_nonce", "_pair_nonce", "_request", "_verified", "_sealed"):
        object.__setattr__(forged, field, getattr(completion, field))

    with pytest.raises(ValueError):
        verifier_peer._consume_completion_and_call_journal_v1(forged)

    assert state._completion_lifecycle_records[id(completion)].state is protocol._CompletionLifecycleV1.PENDING
    assert journal.callback_count == 0
    assert verifier_peer._consume_completion_and_call_journal_v1(completion) is protocol._JournalCompletionCallbackResultV1.COMMITTED
    assert journal.callback_count == 1


def test_active_request_rejects_duplicate_without_creating_second_authority() -> None:
    state, _, journal_peer, _ = _state_and_pair()
    request = journal_peer._issue_registered_owner_verification_request_v1()
    record_count = len(state._records)

    with pytest.raises(ValueError):
        journal_peer._issue_registered_owner_verification_request_v1()

    assert tuple(state._requests.values()) == (request,)
    assert state._completions == {}
    assert len(state._records) == record_count


def test_active_completion_rejects_prior_p1_reproduction_without_new_authority() -> None:
    state, journal, journal_peer, verifier_peer = _state_and_pair()
    request = journal_peer._issue_registered_owner_verification_request_v1()
    completion = verifier_peer._consume_request_and_issue_completion_v1(request, _verified())
    record_count = len(state._records)

    with pytest.raises(ValueError):
        journal_peer._issue_registered_owner_verification_request_v1()

    assert state._requests == {}
    assert tuple(state._completions.values()) == (completion,)
    assert len(state._records) == record_count
    assert journal.callback_count == 0
    assert verifier_peer._consume_completion_and_call_journal_v1(completion) is protocol._JournalCompletionCallbackResultV1.COMMITTED
    assert journal.callback_count == 1


def test_exclusivity_is_exactly_scoped_to_pair_and_delivery_identity() -> None:
    state = protocol._create_isolated_test_protocol_state_v1()
    channel = state.take_bootstrap()
    channel._register_production_journal_class_once_v1(_TestJournal)
    first_journal = _TestJournal()
    first_journal_peer, first_verifier_peer = state.create_pair(first_journal)
    second_journal = _TestJournal()
    second_journal_peer, _ = state.create_pair(second_journal)

    request = first_journal_peer._issue_registered_owner_verification_request_v1()
    completion = first_verifier_peer._consume_request_and_issue_completion_v1(request, _verified())
    assert second_journal_peer._issue_registered_owner_verification_request_v1().facts.delivery_identity == "delivery:001"

    first_journal.delivery_identity = "delivery:002"
    assert first_journal_peer._issue_registered_owner_verification_request_v1().facts.delivery_identity == "delivery:002"
    assert tuple(state._completions.values()) == (completion,)


def test_competing_request_issuances_have_one_winner_under_shared_lock() -> None:
    state, _, journal_peer, _ = _state_and_pair()
    barrier = threading.Barrier(3)
    outcomes: list[object] = []

    def issue() -> None:
        barrier.wait()
        try:
            outcomes.append(journal_peer._issue_registered_owner_verification_request_v1())
        except ValueError as error:
            outcomes.append(error)

    threads = [threading.Thread(target=issue) for _ in range(2)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()

    requests = [item for item in outcomes if type(item) is protocol._RegisteredOwnerVerificationRequestV1]
    failures = [item for item in outcomes if type(item) is ValueError]
    assert len(requests) == 1
    assert len(failures) == 1
    assert tuple(state._requests.values()) == tuple(requests)
    assert state._completions == {}


def test_active_completion_rejects_competing_request_issuance_atomically() -> None:
    state, _, journal_peer, verifier_peer = _state_and_pair()
    request = journal_peer._issue_registered_owner_verification_request_v1()
    completion = verifier_peer._consume_request_and_issue_completion_v1(request, _verified())
    barrier = threading.Barrier(3)
    outcomes: list[object] = []

    def issue() -> None:
        barrier.wait()
        try:
            outcomes.append(journal_peer._issue_registered_owner_verification_request_v1())
        except ValueError as error:
            outcomes.append(error)

    threads = [threading.Thread(target=issue) for _ in range(2)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()

    assert all(type(item) is ValueError for item in outcomes)
    assert state._requests == {}
    assert tuple(state._completions.values()) == (completion,)


def test_cross_pair_request_and_completion_are_rejected() -> None:
    _, _, first_journal_peer, first_verifier_peer = _state_and_pair()
    _, _, second_journal_peer, second_verifier_peer = _state_and_pair()
    request = first_journal_peer._issue_registered_owner_verification_request_v1()
    with pytest.raises(ValueError):
        second_verifier_peer._consume_request_and_issue_completion_v1(request, _verified())
    completion = first_verifier_peer._consume_request_and_issue_completion_v1(request, _verified())
    with pytest.raises(ValueError):
        second_verifier_peer._consume_completion_and_call_journal_v1(completion)
    assert second_journal_peer._issue_registered_owner_verification_request_v1().facts.delivery_identity == "delivery:001"


def test_pair_rebinding_and_pre_registration_pair_creation_fail_closed() -> None:
    state = protocol._create_isolated_test_protocol_state_v1()
    with pytest.raises(ValueError):
        state.create_pair(_TestJournal())
    journal = _TestJournal()
    authority = state.issue_test_authority(_TestJournal)
    state.create_pair(journal, authority)
    with pytest.raises(ValueError):
        state.create_pair(journal)


def test_invalid_first_bootstrap_candidate_consumes_state_permanently() -> None:
    state = protocol._create_isolated_test_protocol_state_v1()
    channel = state.take_bootstrap()
    with pytest.raises(ValueError):
        channel._register_production_journal_class_once_v1(object)  # type: ignore[arg-type]
    assert state._bootstrap_state is protocol._BootstrapState.BOOTSTRAP_FAILED
    with pytest.raises(ValueError):
        channel._register_production_journal_class_once_v1(_TestJournal)
    with pytest.raises(ValueError):
        state.take_bootstrap()


def test_production_class_registration_is_exact_and_one_shot() -> None:
    state = protocol._create_isolated_test_protocol_state_v1()
    channel = state.take_bootstrap()
    channel._register_production_journal_class_once_v1(_TestJournal)
    assert state._registered_class is _TestJournal
    with pytest.raises(ValueError):
        channel._register_production_journal_class_once_v1(_TestJournal)
    with pytest.raises(protocol._ProductionJournalClassAlreadyRegisteredV1):
        state.take_bootstrap()


def test_concurrent_bootstrap_attempts_have_one_winner() -> None:
    state = protocol._create_isolated_test_protocol_state_v1()
    outcomes: list[object] = []

    def take() -> None:
        try:
            outcomes.append(state.take_bootstrap())
        except Exception as error:
            outcomes.append(type(error))

    threads = [threading.Thread(target=take) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sum(isinstance(item, protocol._ProductionJournalBootstrapChannelV1) for item in outcomes) == 1


def test_callback_exception_before_commit_maps_to_not_committed() -> None:
    _, journal, journal_peer, verifier_peer = _state_and_pair()
    journal.callback = RuntimeError("lost acknowledgement")
    request = journal_peer._issue_registered_owner_verification_request_v1()
    completion = verifier_peer._consume_request_and_issue_completion_v1(request, _verified())
    assert verifier_peer._consume_completion_and_call_journal_v1(completion) is protocol._JournalCompletionCallbackResultV1.NOT_COMMITTED


def test_test_state_never_mutates_production_bootstrap_state() -> None:
    assert protocol._PRODUCTION_STATE._bootstrap_state is protocol._BootstrapState.UNISSUED
    state = protocol._create_isolated_test_protocol_state_v1()
    state.take_bootstrap()
    assert protocol._PRODUCTION_STATE._bootstrap_state is protocol._BootstrapState.UNISSUED
