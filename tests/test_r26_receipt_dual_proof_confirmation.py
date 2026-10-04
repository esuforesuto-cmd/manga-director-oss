"""Focused private IMP-09 proof-to-Receipt handoff coverage."""

from __future__ import annotations

import copy
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from typing import TypeVar

import pytest

from manga_director.production import future_real_delivery_r26_reconciliation as r26
from manga_director.production import next_generation_durable_application_commit_receipt as receipt
from manga_director.production.next_generation_workflow_application_ledger import (
    WorkflowApplicationLedgerBindingDTO,
)
from manga_director.workflow import localfile_external_generated_application as external
from manga_director.workflow import localfile_private_real_delivery_composition as private
from manga_director.workflow.localfile_external_generated_application import (
    _ExternalApplicationFenceContext,
)
from manga_director.workflow.page_execution_fence import WindowsPageExecutionFence

_T = TypeVar("_T")


@pytest.fixture(autouse=True)
def _clear_r26_private_registries() -> None:
    with r26._R26_REGISTRY_LOCK:
        r26._ISSUED.clear()
        r26._CONSUMED.clear()
        r26._PROOFS_BY_INVOCATION.clear()
        r26._RECEIPT_PROJECTIONS.clear()
        r26._CONSUMED_RECEIPT_PROJECTIONS.clear()


def _binding() -> WorkflowApplicationLedgerBindingDTO:
    return WorkflowApplicationLedgerBindingDTO(
        attempt_id="attempt-one",
        authorization_id="authorization-one",
        project_id="project-one",
        page_id="page-one",
        target_page_reference="page-one",
        provider_reference="provider-one",
        output_asset_id="asset-one",
        source_state="PromptBuilt",
        target_state="Generated",
    )


def _issued_proof(
    *,
    repository: object | None = None,
    composition: object | None = None,
    coordinator: object | None = None,
) -> tuple[object, object, WorkflowApplicationLedgerBindingDTO, object, object, object]:
    binding = _binding()
    repository = object() if repository is None else repository
    composition = object() if composition is None else composition
    coordinator = object() if coordinator is None else coordinator
    invocation = object()
    factory = object.__new__(r26._R26ReconciliationProofFactoryV1)
    object.__setattr__(factory, "_nonce", object())
    object.__setattr__(factory, "_repository", repository)
    object.__setattr__(factory, "_r25", composition)
    object.__setattr__(factory, "_coordinator", coordinator)
    object.__setattr__(factory, "_issued", set())
    proof = object.__new__(r26._AuthoritativePostCASReconciliationProofV1)
    post_identity = (7, "a" * 64, "attestation-private-only")
    digest = r26._r27_application_binding_identity(binding)
    object.__setattr__(proof, "_seal", r26._R26_PROOF_SEAL)
    object.__setattr__(proof, "_binding_digest", digest)
    object.__setattr__(proof, "_nonce", factory._nonce)
    object.__setattr__(proof, "_post_identity", post_identity)
    object.__setattr__(proof, "_invocation", invocation)
    object.__setattr__(proof, "_composition", composition)
    r26._ISSUED[proof] = (factory, invocation, digest, post_identity, proof, binding)
    r26._PROOFS_BY_INVOCATION[invocation] = proof
    factory._issued.add(proof)
    return factory, proof, binding, repository, composition, coordinator


def _consume_projection() -> tuple[
    object, object, WorkflowApplicationLedgerBindingDTO, object, object, object, object
]:
    factory, proof, binding, repository, composition, coordinator = _issued_proof()
    invocation = proof._invocation
    result = r26._consume_r26_reconciliation_proof_into_receipt_projection_v1(
        proof, factory, binding, invocation_authority=invocation
    )
    assert result.outcome == "SEALED_RECONCILIATION_PROOF_ISSUED"
    assert result.projection is not None
    return factory, result.projection, binding, repository, composition, coordinator, invocation


def _concurrent(count: int, operation: Callable[[], _T]) -> list[_T]:
    barrier = Barrier(count)

    def _run() -> _T:
        barrier.wait()
        return operation()

    with ThreadPoolExecutor(max_workers=count) as executor:
        return [future.result() for future in [executor.submit(_run) for _ in range(count)]]


def _tree_bytes(root: Path) -> dict[str, bytes]:
    """Snapshot only durable bytes; timestamps are intentionally irrelevant."""

    return {
        item.relative_to(root).as_posix(): item.read_bytes()
        for item in sorted(root.rglob("*"))
        if item.is_file()
    }


def _unexpected_successor_effect(*_args: object, **_kwargs: object) -> None:
    raise AssertionError("IMP-09 must not invoke successor authority")


def _live_receipt_projection(
    tmp_path: Path, suffix: str
) -> tuple[
    object,
    WorkflowApplicationLedgerBindingDTO,
    object,
    object,
    WindowsPageExecutionFence,
    object,
    object,
    object,
]:
    root = private._create_private_real_delivery_workflow_host_v1(
        tmp_path / suffix
    )._start_private_real_delivery_composition_v1()
    coordinator = root._composition.external_application
    binding = _binding()
    fence = WindowsPageExecutionFence(binding.project_id, binding.page_id)
    fence.acquire()
    context = _ExternalApplicationFenceContext._create(
        binding, SimpleNamespace(revision=7, fingerprint="a" * 64)
    )
    coordinator._r26_active_fence_contexts.add(context)
    invocation = coordinator._issue_r26_fence_invocation_authority_v1(binding, fence, context)
    coordinator._r26_fence_invocations.discard(invocation)
    coordinator._r26_fence_invocations_by_context.pop(context, None)
    object.__setattr__(invocation, "_used", True)
    factory = coordinator._r26_proof_factory
    projection = object.__new__(r26._PrivateConsumedR26ReceiptProjectionV1)
    digest = r26._r27_application_binding_identity(binding)
    object.__setattr__(projection, "_seal", r26._R26_PROOF_SEAL)
    object.__setattr__(projection, "_binding_digest", digest)
    object.__setattr__(projection, "_nonce", factory._nonce)
    object.__setattr__(projection, "_invocation", invocation)
    object.__setattr__(projection, "_composition", coordinator._r25_localfile_composition)
    r26._RECEIPT_PROJECTIONS[projection] = (
        factory,
        invocation,
        binding,
        digest,
        7,
        "a" * 64,
        coordinator._r25_localfile_composition,
        projection,
    )
    return (
        coordinator,
        binding,
        coordinator._r25_localfile_composition,
        invocation,
        fence,
        context,
        projection,
        root,
    )


def _pending_receipt_confirmation(
    tmp_path: Path, suffix: str
) -> tuple[object, WorkflowApplicationLedgerBindingDTO, object, object, WindowsPageExecutionFence, object]:
    coordinator, binding, composition, invocation, fence, context, projection, root = _live_receipt_projection(
        tmp_path, suffix
    )
    factory = coordinator._r26_proof_factory
    assert (
        coordinator._receipt_service._commit_consumed_r26_projection_v1(
            projection,
            factory,
            binding,
            repository=root._repository,
            composition=composition,
            coordinator=coordinator,
            invocation_authority=invocation,
            receipt_store=coordinator._receipt_store,
        ).outcome
        == "RECEIPT_CONFIRMED"
    )
    assert coordinator._record_r26_pending_receipt_confirmation_v1(
        factory, binding, composition, invocation, projection
    )
    return coordinator, binding, composition, invocation, fence, context


def test_existing_exact_receipt_requires_current_projection_consumption_before_confirmation(
    tmp_path: Path,
) -> None:
    coordinator, binding, composition, invocation, fence, context, projection, root = _live_receipt_projection(
        tmp_path, "existing-receipt"
    )
    factory = coordinator._r26_proof_factory
    existing = receipt._receipt(binding, 7, "a" * 64)
    assert existing is not None
    assert coordinator._receipt_store.commit(existing).outcome == "committed"

    assert not coordinator._record_r26_pending_receipt_confirmation_v1(
        factory, binding, composition, invocation, projection
    )
    assert invocation not in coordinator._r26_pending_receipt_confirmations
    assert (
        coordinator._issue_exact_receipt_reconciliation_confirmation_v1(
            factory, binding, composition, invocation
        )
        is None
    )

    assert (
        coordinator._receipt_service._commit_consumed_r26_projection_v1(
            projection,
            factory,
            binding,
            repository=root._repository,
            composition=composition,
            coordinator=coordinator,
            invocation_authority=invocation,
            receipt_store=coordinator._receipt_store,
        ).outcome
        == "RECEIPT_CONFIRMED"
    )
    assert coordinator._record_r26_pending_receipt_confirmation_v1(
        factory, binding, composition, invocation, projection
    )
    assert coordinator._issue_exact_receipt_reconciliation_confirmation_v1(
        factory, binding, composition, invocation
    ) is not None
    coordinator._r26_active_fence_contexts.discard(context)
    fence.release()


def test_consumed_projection_stage_rejects_foreign_or_stale_invocation(tmp_path: Path) -> None:
    coordinator, binding, composition, invocation, fence, context, projection, root = _live_receipt_projection(
        tmp_path, "foreign-stage"
    )
    factory = coordinator._r26_proof_factory
    assert (
        coordinator._receipt_service._commit_consumed_r26_projection_v1(
            projection,
            factory,
            binding,
            repository=root._repository,
            composition=composition,
            coordinator=coordinator,
            invocation_authority=invocation,
            receipt_store=coordinator._receipt_store,
        ).outcome
        == "RECEIPT_CONFIRMED"
    )
    assert not coordinator._record_r26_pending_receipt_confirmation_v1(
        factory, binding, composition, object(), projection
    )
    coordinator._r26_active_fence_contexts.discard(context)
    fence.release()
    assert not coordinator._record_r26_pending_receipt_confirmation_v1(
        factory, binding, composition, invocation, projection
    )


def test_confirmed_invocation_tombstone_cannot_restage_another_confirmation(
    tmp_path: Path,
) -> None:
    coordinator, binding, composition, invocation, fence, context, projection, _ = _live_receipt_projection(
        tmp_path, "terminal-restage"
    )
    factory = coordinator._r26_proof_factory
    assert (
        coordinator._receipt_service._commit_consumed_r26_projection_v1(
            projection,
            factory,
            binding,
            repository=coordinator._page_store._repository,
            composition=composition,
            coordinator=coordinator,
            invocation_authority=invocation,
            receipt_store=coordinator._receipt_store,
        ).outcome
        == "RECEIPT_CONFIRMED"
    )
    assert coordinator._record_r26_pending_receipt_confirmation_v1(
        factory, binding, composition, invocation, projection
    )
    first = coordinator._issue_exact_receipt_reconciliation_confirmation_v1(
        factory, binding, composition, invocation
    )
    assert first is not None
    for _ in range(3):
        assert not coordinator._record_r26_pending_receipt_confirmation_v1(
            factory, binding, composition, invocation, projection
        )
        assert (
            coordinator._issue_exact_receipt_reconciliation_confirmation_v1(
                factory, binding, composition, invocation
            )
            is None
        )
    assert len(coordinator._r26_receipt_confirmation_records) == 1
    coordinator._r26_active_fence_contexts.discard(context)
    fence.release()


def test_exact_proof_consumes_to_registry_projection_once() -> None:
    factory, projection, binding, repository, composition, coordinator, invocation = (
        _consume_projection()
    )

    facts = r26._consume_r26_receipt_projection_for_receipt_v1(
        projection,
        factory,
        binding,
        repository=repository,
        composition=composition,
        coordinator=coordinator,
        invocation_authority=invocation,
    )

    assert facts.outcome == "SEALED_RECONCILIATION_PROOF_ISSUED"
    assert facts.binding == binding
    assert facts.output_asset_id == binding.output_asset_id
    assert facts.post_commit_revision == 7
    assert facts.post_commit_fingerprint == "a" * 64
    assert (
        r26._consume_r26_receipt_projection_for_receipt_v1(
            projection,
            factory,
            binding,
            repository=repository,
            composition=composition,
            coordinator=coordinator,
            invocation_authority=invocation,
        ).outcome
        == "CONSUMED"
    )


def test_proof_and_projection_reject_reconstruction_copy_and_foreign_authority() -> None:
    factory, proof, binding, repository, composition, coordinator = _issued_proof()
    forged = object.__new__(r26._AuthoritativePostCASReconciliationProofV1)
    assert (
        r26._consume_r26_reconciliation_proof_into_receipt_projection_v1(
            forged, factory, binding, invocation_authority=object()
        ).outcome
        == "AUTHORITY_REJECTED"
    )
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        copy.copy(proof)
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        copy.deepcopy(proof)
    projection = r26._consume_r26_reconciliation_proof_into_receipt_projection_v1(
        proof, factory, binding, invocation_authority=proof._invocation
    ).projection
    assert projection is not None
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        copy.copy(projection)
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        copy.deepcopy(projection)
    assert (
        r26._consume_r26_receipt_projection_for_receipt_v1(
            projection,
            factory,
            binding,
            repository=object(),
            composition=composition,
            coordinator=coordinator,
            invocation_authority=proof._invocation,
        ).outcome
        == "AUTHORITY_REJECTED"
    )


def test_wrong_binding_or_invocation_cannot_consume_the_live_projection() -> None:
    factory, projection, binding, repository, composition, coordinator, invocation = (
        _consume_projection()
    )
    replacement = binding.model_copy(update={"output_asset_id": "asset-two"})

    assert (
        r26._consume_r26_receipt_projection_for_receipt_v1(
            projection,
            factory,
            replacement,
            repository=repository,
            composition=composition,
            coordinator=coordinator,
            invocation_authority=invocation,
        ).outcome
        == "AUTHORITY_REJECTED"
    )
    assert (
        r26._consume_r26_receipt_projection_for_receipt_v1(
            projection,
            factory,
            binding,
            repository=repository,
            composition=composition,
            coordinator=coordinator,
            invocation_authority=object(),
        ).outcome
        == "AUTHORITY_REJECTED"
    )
    assert (
        r26._consume_r26_receipt_projection_for_receipt_v1(
            projection,
            factory,
            binding,
            repository=repository,
            composition=composition,
            coordinator=coordinator,
            invocation_authority=invocation,
        ).outcome
        == "SEALED_RECONCILIATION_PROOF_ISSUED"
    )


def test_direct_proof_slot_substitution_is_not_projection_authority() -> None:
    factory, proof, binding, _, composition, _ = _issued_proof()
    object.__setattr__(proof, "_post_identity", (8, "b" * 64, "replacement"))

    assert (
        r26._consume_r26_reconciliation_proof_into_receipt_projection_v1(
            proof, factory, binding, invocation_authority=proof._invocation
        ).outcome
        == "AUTHORITY_REJECTED"
    )
    assert proof in r26._ISSUED
    assert proof._composition is composition


def test_crash_seam_1_before_proof_consumption_leaves_only_the_live_proof() -> None:
    factory, proof, binding, _, _, _ = _issued_proof()

    assert r26._ISSUED.get(proof) is not None
    assert proof in factory._issued
    assert r26._PROOFS_BY_INVOCATION.get(proof._invocation) is proof
    assert not r26._RECEIPT_PROJECTIONS
    assert not r26._CONSUMED_RECEIPT_PROJECTIONS

    consumed = r26._consume_r26_reconciliation_proof_into_receipt_projection_v1(
        proof, factory, binding, invocation_authority=proof._invocation
    )
    assert consumed.outcome == "SEALED_RECONCILIATION_PROOF_ISSUED"
    assert consumed.projection is not None


def test_crash_seam_2_after_proof_consumption_has_one_volatile_projection(
    tmp_path: Path,
) -> None:
    factory, proof, binding, repository, composition, coordinator = _issued_proof()
    consumed = r26._consume_r26_reconciliation_proof_into_receipt_projection_v1(
        proof, factory, binding, invocation_authority=proof._invocation
    )
    projection = consumed.projection
    store = receipt.LocalDurableApplicationCommitReceiptStore(tmp_path / "owner")

    assert consumed.outcome == "SEALED_RECONCILIATION_PROOF_ISSUED"
    assert projection is not None
    assert proof not in r26._ISSUED
    assert proof in r26._CONSUMED
    assert tuple(r26._RECEIPT_PROJECTIONS) == (projection,)
    assert store.lookup_exact(binding, 7, "a" * 64).outcome == "missing"
    assert not r26._CONSUMED_RECEIPT_PROJECTIONS

    r26._RECEIPT_PROJECTIONS.clear()
    assert (
        r26._consume_r26_receipt_projection_for_receipt_v1(
            projection,
            factory,
            binding,
            repository=repository,
            composition=composition,
            coordinator=coordinator,
            invocation_authority=proof._invocation,
        ).outcome
        == "AUTHORITY_REJECTED"
    )
    assert store.lookup_exact(binding, 7, "a" * 64).outcome == "missing"

    next_factory, next_proof, _, _, _, _ = _issued_proof(
        repository=repository, composition=composition, coordinator=coordinator
    )
    next_projection = r26._consume_r26_reconciliation_proof_into_receipt_projection_v1(
        next_proof, next_factory, binding, invocation_authority=next_proof._invocation
    ).projection
    assert next_projection is not None
    facts = r26._consume_r26_receipt_projection_for_receipt_v1(
        next_projection,
        next_factory,
        binding,
        repository=repository,
        composition=composition,
        coordinator=coordinator,
        invocation_authority=next_proof._invocation,
    )
    assert facts.outcome == "SEALED_RECONCILIATION_PROOF_ISSUED"
    assert (
        r26._consume_r26_receipt_projection_for_receipt_v1(
            next_projection,
            next_factory,
            binding,
            repository=repository,
            composition=composition,
            coordinator=coordinator,
            invocation_authority=next_proof._invocation,
        ).outcome
        == "CONSUMED"
    )


def test_reconstructed_equal_value_projection_is_not_authoritative() -> None:
    factory, projection, binding, repository, composition, coordinator, invocation = (
        _consume_projection()
    )
    reconstructed = object.__new__(r26._PrivateConsumedR26ReceiptProjectionV1)
    for name in ("_seal", "_binding_digest", "_nonce", "_invocation", "_composition"):
        object.__setattr__(reconstructed, name, getattr(projection, name))

    assert (
        r26._consume_r26_receipt_projection_for_receipt_v1(
            reconstructed,
            factory,
            binding,
            repository=repository,
            composition=composition,
            coordinator=coordinator,
            invocation_authority=invocation,
        ).outcome
        == "AUTHORITY_REJECTED"
    )
    assert projection in r26._RECEIPT_PROJECTIONS


def test_value_equal_foreign_projection_is_not_authoritative() -> None:
    factory, projection, binding, repository, composition, coordinator, invocation = (
        _consume_projection()
    )
    _, foreign_projection, foreign_binding, _, _, _, foreign_invocation = _consume_projection()
    assert foreign_binding == binding
    for name in ("_seal", "_binding_digest", "_nonce", "_invocation", "_composition"):
        object.__setattr__(foreign_projection, name, getattr(projection, name))

    assert (
        r26._consume_r26_receipt_projection_for_receipt_v1(
            foreign_projection,
            factory,
            binding,
            repository=repository,
            composition=composition,
            coordinator=coordinator,
            invocation_authority=invocation,
        ).outcome
        == "AUTHORITY_REJECTED"
    )
    assert foreign_projection in r26._RECEIPT_PROJECTIONS
    assert foreign_invocation is not invocation


def test_receipt_commit_readback_and_confirmation_are_exact_and_one_shot(tmp_path: Path) -> None:
    factory, projection, binding, repository, composition, coordinator, invocation = (
        _consume_projection()
    )
    service = receipt.DurableApplicationCommitReceiptService()
    store = receipt.LocalDurableApplicationCommitReceiptStore(tmp_path / "owner")

    class _Coordinator:
        pass

    exact_coordinator = _Coordinator()
    exact_coordinator._receipt_service = service
    exact_coordinator._receipt_store = store
    object.__setattr__(factory, "_coordinator", exact_coordinator)
    # The projection is tied to the factory's exact coordinator at validation time.
    entry = r26._RECEIPT_PROJECTIONS[projection]
    r26._RECEIPT_PROJECTIONS[projection] = (
        factory,
        invocation,
        binding,
        entry[3],
        entry[4],
        entry[5],
        composition,
        projection,
    )
    outcome = service._commit_consumed_r26_projection_v1(
        projection,
        factory,
        binding,
        repository=repository,
        composition=composition,
        coordinator=exact_coordinator,
        invocation_authority=invocation,
        receipt_store=store,
    )

    assert outcome.outcome == "RECEIPT_CONFIRMED"
    assert outcome == receipt._R26ReceiptCommitOutcomeV1("RECEIPT_CONFIRMED")
    assert copy.copy(outcome) == outcome
    assert copy.deepcopy(outcome) == outcome


def test_receipt_outcome_is_ordinary_data_and_has_no_confirmation_registry() -> None:
    outcome = receipt._R26ReceiptCommitOutcomeV1("RECEIPT_CONFIRMED")

    assert outcome.outcome == "RECEIPT_CONFIRMED"
    assert copy.copy(outcome) == outcome
    assert copy.deepcopy(outcome) == outcome
    assert not hasattr(outcome, "_seal")
    assert not hasattr(receipt, "_R26ReceiptCommitResultV1")
    assert not hasattr(receipt, "_R26_RECEIPT_RESULTS")


def test_live_projection_confirmation_reader_requires_exact_authority_tuple() -> None:
    factory, projection, binding, repository, composition, coordinator, invocation = (
        _consume_projection()
    )

    assert r26._read_live_r26_receipt_projection_facts_for_confirmation_v1(
        projection,
        factory,
        binding,
        repository=repository,
        composition=composition,
        coordinator=coordinator,
        invocation_authority=invocation,
    ) == (r26._r27_application_binding_identity(binding), 7, "a" * 64)
    assert r26._read_live_r26_receipt_projection_facts_for_confirmation_v1(
        projection,
        factory,
        binding,
        repository=object(),
        composition=composition,
        coordinator=coordinator,
        invocation_authority=invocation,
    ) is None
    assert r26._read_live_r26_receipt_projection_facts_for_confirmation_v1(
        projection,
        factory,
        binding,
        repository=repository,
        composition=object(),
        coordinator=coordinator,
        invocation_authority=invocation,
    ) is None
    assert r26._read_live_r26_receipt_projection_facts_for_confirmation_v1(
        projection,
        factory,
        binding,
        repository=repository,
        composition=composition,
        coordinator=object(),
        invocation_authority=invocation,
    ) is None
    assert r26._read_live_r26_receipt_projection_facts_for_confirmation_v1(
        projection,
        factory,
        binding.model_copy(update={"output_asset_id": "asset-two"}),
        repository=repository,
        composition=composition,
        coordinator=coordinator,
        invocation_authority=invocation,
    ) is None


@pytest.mark.parametrize("outcome", ["missing", "corrupt", "conflict"])
def test_confirmation_requires_fresh_exact_durable_receipt_readback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    coordinator, binding, composition, invocation, fence, context = _pending_receipt_confirmation(
        tmp_path.parent, outcome
    )
    factory = coordinator._r26_proof_factory
    monkeypatch.setattr(
        coordinator._receipt_service,
        "lookup_exact",
        lambda *_args, **_kwargs: receipt.DurableApplicationCommitReceiptExactLookupResult(outcome),
    )

    assert (
        coordinator._issue_exact_receipt_reconciliation_confirmation_v1(
            factory, binding, composition, invocation
        )
        is None
    )
    assert invocation in coordinator._r26_pending_receipt_confirmations
    assert not coordinator._r26_receipt_confirmations
    coordinator._r26_active_fence_contexts.discard(context)
    fence.release()


def test_confirmation_rejects_foreign_tuple_and_released_fence(tmp_path: Path) -> None:
    coordinator, binding, composition, invocation, fence, context = _pending_receipt_confirmation(
        tmp_path.parent, "foreign"
    )
    factory = coordinator._r26_proof_factory
    assert (
        coordinator._issue_exact_receipt_reconciliation_confirmation_v1(
            object(), binding, composition, invocation
        )
        is None
    )
    assert (
        coordinator._issue_exact_receipt_reconciliation_confirmation_v1(
            factory,
            binding.model_copy(update={"output_asset_id": "asset-two"}),
            composition,
            invocation,
        )
        is None
    )
    assert (
        coordinator._issue_exact_receipt_reconciliation_confirmation_v1(
            factory, binding, object(), invocation
        )
        is None
    )
    fence.release()
    assert (
        coordinator._issue_exact_receipt_reconciliation_confirmation_v1(
            factory, binding, composition, invocation
        )
        is None
    )
    assert invocation in coordinator._r26_pending_receipt_confirmations
    coordinator._r26_active_fence_contexts.discard(context)


def test_durable_receipt_without_coordinator_pending_facts_cannot_confirm(tmp_path: Path) -> None:
    coordinator, binding, composition, invocation, fence, context = _pending_receipt_confirmation(
        tmp_path.parent, "no-pending"
    )
    factory = coordinator._r26_proof_factory
    coordinator._r26_pending_receipt_confirmations.pop(invocation)

    assert (
        coordinator._issue_exact_receipt_reconciliation_confirmation_v1(
            factory, binding, composition, invocation
        )
        is None
    )
    assert not coordinator._r26_receipt_confirmations
    coordinator._r26_active_fence_contexts.discard(context)
    fence.release()


def test_confirmation_performs_no_receipt_write_after_fresh_readback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    coordinator, binding, composition, invocation, fence, context = _pending_receipt_confirmation(
        tmp_path.parent, "no-confirmation-write"
    )
    factory = coordinator._r26_proof_factory
    monkeypatch.setattr(
        coordinator._receipt_store,
        "commit",
        lambda _receipt: (_ for _ in ()).throw(AssertionError("confirmation must not write Receipt")),
    )

    assert coordinator._issue_exact_receipt_reconciliation_confirmation_v1(
        factory, binding, composition, invocation
    ) is not None
    assert len(coordinator._r26_receipt_confirmation_records) == 1
    coordinator._r26_active_fence_contexts.discard(context)
    fence.release()


def test_crash_seam_10_after_readback_cannot_issue_receipt_only_confirmation(
    tmp_path: Path,
) -> None:
    coordinator, binding, composition, invocation, fence, context = _pending_receipt_confirmation(
        tmp_path.parent, "after-readback"
    )
    factory = coordinator._r26_proof_factory
    root = tmp_path.parent / "after-readback"
    assert coordinator._receipt_service.lookup_exact(
        binding,
        post_commit_revision=7,
        post_commit_fingerprint="a" * 64,
        receipt_store=coordinator._receipt_store,
    ).outcome == "found"
    assert invocation in coordinator._r26_pending_receipt_confirmations
    before = _tree_bytes(root)

    coordinator._r26_pending_receipt_confirmations.pop(invocation)
    assert (
        coordinator._issue_exact_receipt_reconciliation_confirmation_v1(
            factory, binding, composition, invocation
        )
        is None
    )
    assert not coordinator._r26_receipt_confirmations
    assert _tree_bytes(root) == before
    coordinator._r26_active_fence_contexts.discard(context)
    fence.release()


def test_imp09_success_confirmation_has_no_ledger_state_cas_generated_provider_r27_r29_r30_r31_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    coordinator, binding, composition, invocation, fence, context = _pending_receipt_confirmation(
        tmp_path.parent, "negative-success"
    )
    root = tmp_path.parent / "negative-success"
    before = _tree_bytes(root)
    page_store_type = type(coordinator._page_store)
    ledger_service_type = type(coordinator._ledger_service)
    state_machine_type = type(coordinator._state_machine)
    assert coordinator._r27_publication_factory is not None
    assert coordinator._r29_activation_policy is not None

    for method in ("prepare", "finalize", "lookup_applied"):
        monkeypatch.setattr(ledger_service_type, method, _unexpected_successor_effect)
    monkeypatch.setattr(state_machine_type, "validate_transition", _unexpected_successor_effect)
    for method in (
        "conditional_commit",
        "_conditional_commit_r27",
        "_activate_and_conditional_commit_r27",
    ):
        monkeypatch.setattr(page_store_type, method, _unexpected_successor_effect, raising=False)
    for name in (
        "_record_normal_r30_pre_cas_provenance_v1",
        "_issue_r30_restart_ingress_v1",
        "_consume_r30_restart_ingress_and_materialize_v1",
        "_materialize_normal_r25_v1",
    ):
        monkeypatch.setattr(external, name, _unexpected_successor_effect)
    monkeypatch.setattr(
        coordinator._r27_publication_factory, "_issue", _unexpected_successor_effect
    )
    monkeypatch.setattr(
        coordinator._r27_publication_factory, "_consume_issued", _unexpected_successor_effect
    )
    monkeypatch.setattr(
        coordinator._r29_activation_policy, "_select_first_publication", _unexpected_successor_effect
    )

    assert not hasattr(coordinator, "_provider")
    assert coordinator._issue_exact_receipt_reconciliation_confirmation_v1(
        coordinator._r26_proof_factory, binding, composition, invocation
    ) is not None
    assert _tree_bytes(root) == before
    assert len(coordinator._r26_receipt_confirmation_records) == 1
    coordinator._r26_active_fence_contexts.discard(context)
    fence.release()


def test_imp09_exact_receipt_replay_has_no_successor_effects(tmp_path: Path) -> None:
    service = receipt.DurableApplicationCommitReceiptService()
    store = receipt.LocalDurableApplicationCommitReceiptStore(tmp_path / "owner")

    class _Coordinator:
        pass

    coordinator = _Coordinator()
    coordinator._receipt_service = service
    coordinator._receipt_store = store
    first_factory, first_projection, binding, repository, composition, _, first_invocation = (
        _consume_projection()
    )
    object.__setattr__(first_factory, "_coordinator", coordinator)
    assert service._commit_consumed_r26_projection_v1(
        first_projection,
        first_factory,
        binding,
        repository=repository,
        composition=composition,
        coordinator=coordinator,
        invocation_authority=first_invocation,
        receipt_store=store,
    ).outcome == "RECEIPT_CONFIRMED"
    before = _tree_bytes(tmp_path / "owner")

    factory, proof, same_binding, _, _, _ = _issued_proof(
        repository=repository, composition=composition, coordinator=coordinator
    )
    projection = r26._consume_r26_reconciliation_proof_into_receipt_projection_v1(
        proof, factory, same_binding, invocation_authority=proof._invocation
    ).projection
    assert projection is not None
    assert service._commit_consumed_r26_projection_v1(
        projection,
        factory,
        same_binding,
        repository=repository,
        composition=composition,
        coordinator=coordinator,
        invocation_authority=proof._invocation,
        receipt_store=store,
    ).outcome == "RECEIPT_CONFIRMED"
    assert _tree_bytes(tmp_path / "owner") == before
    assert not hasattr(coordinator, "_ledger_service")


def test_imp09_receipt_failure_has_no_successor_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    factory, projection, binding, repository, composition, _, invocation = _consume_projection()
    service = receipt.DurableApplicationCommitReceiptService()
    store = receipt.LocalDurableApplicationCommitReceiptStore(tmp_path / "owner")

    class _Coordinator:
        pass

    coordinator = _Coordinator()
    coordinator._receipt_service = service
    coordinator._receipt_store = store
    object.__setattr__(factory, "_coordinator", coordinator)
    before = _tree_bytes(tmp_path / "owner")
    monkeypatch.setattr(store, "commit", _unexpected_successor_effect)

    assert service._commit_consumed_r26_projection_v1(
        projection,
        factory,
        binding,
        repository=repository,
        composition=composition,
        coordinator=coordinator,
        invocation_authority=invocation,
        receipt_store=store,
    ).outcome == "RECOVERY_REQUIRED"
    assert _tree_bytes(tmp_path / "owner") == before
    assert projection in r26._CONSUMED_RECEIPT_PROJECTIONS
    assert not hasattr(coordinator, "_ledger_service")


def test_imp09_has_no_public_api_cli_mcp_http_or_plugin_provider_selector() -> None:
    project_root = Path(__file__).parents[1]
    public_entrypoints = (
        "src/manga_director/__init__.py",
        "src/manga_director/production/__init__.py",
        "src/manga_director/workflow/__init__.py",
        "src/manga_director/cli/app.py",
        "src/manga_director/mcp",
        "src/manga_director/api",
        "src/manga_director/plugins",
    )

    for relative in public_entrypoints:
        location = project_root / relative
        files = (location,) if location.is_file() else tuple(location.rglob("*.py"))
        assert all("r26" not in item.read_text(encoding="utf-8").lower() for item in files)


def test_receipt_projection_commit_rejects_foreign_owner_without_consuming_projection(
    tmp_path: Path,
) -> None:
    factory, projection, binding, repository, composition, coordinator, invocation = (
        _consume_projection()
    )
    service = receipt.DurableApplicationCommitReceiptService()
    store = receipt.LocalDurableApplicationCommitReceiptStore(tmp_path / "owner")

    assert (
        service._commit_consumed_r26_projection_v1(
            projection,
            factory,
            binding,
            repository=repository,
            composition=composition,
            coordinator=coordinator,
            invocation_authority=invocation,
            receipt_store=store,
        ).outcome
        == "AUTHORITY_REJECTED"
    )
    assert projection in r26._RECEIPT_PROJECTIONS


def test_uncertain_receipt_write_result_consumes_projection_and_requires_reconciliation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    factory, projection, binding, repository, composition, _, invocation = _consume_projection()
    service = receipt.DurableApplicationCommitReceiptService()
    store = receipt.LocalDurableApplicationCommitReceiptStore(tmp_path / "owner")

    class _Coordinator:
        pass

    exact_coordinator = _Coordinator()
    exact_coordinator._receipt_service = service
    exact_coordinator._receipt_store = store
    object.__setattr__(factory, "_coordinator", exact_coordinator)
    monkeypatch.setattr(store, "commit", lambda _receipt: object())

    assert (
        service._commit_consumed_r26_projection_v1(
            projection,
            factory,
            binding,
            repository=repository,
            composition=composition,
            coordinator=exact_coordinator,
            invocation_authority=invocation,
            receipt_store=store,
        ).outcome
        == "RECOVERY_REQUIRED"
    )
    assert projection in r26._CONSUMED_RECEIPT_PROJECTIONS


def test_receipt_failure_consumes_projection_without_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    factory, projection, binding, repository, composition, coordinator, invocation = (
        _consume_projection()
    )
    service = receipt.DurableApplicationCommitReceiptService()
    store = receipt.LocalDurableApplicationCommitReceiptStore(tmp_path / "owner")

    class _Coordinator:
        pass

    exact_coordinator = _Coordinator()
    exact_coordinator._receipt_service = service
    exact_coordinator._receipt_store = store
    object.__setattr__(factory, "_coordinator", exact_coordinator)
    monkeypatch.setattr(store, "commit", lambda _receipt: (_ for _ in ()).throw(OSError("locked")))
    outcome = service._commit_consumed_r26_projection_v1(
        projection,
        factory,
        binding,
        repository=repository,
        composition=composition,
        coordinator=exact_coordinator,
        invocation_authority=invocation,
        receipt_store=store,
    )

    assert outcome.outcome == "RECOVERY_REQUIRED"
    assert (
        r26._consume_r26_receipt_projection_for_receipt_v1(
            projection,
            factory,
            binding,
            repository=repository,
            composition=composition,
            coordinator=exact_coordinator,
            invocation_authority=invocation,
        ).outcome
        == "CONSUMED"
    )


def test_existing_conflicting_receipt_fails_closed_after_projection_consumption(
    tmp_path: Path,
) -> None:
    factory, projection, binding, repository, composition, _, invocation = _consume_projection()
    service = receipt.DurableApplicationCommitReceiptService()
    store = receipt.LocalDurableApplicationCommitReceiptStore(tmp_path / "owner")

    class _Coordinator:
        pass

    exact_coordinator = _Coordinator()
    exact_coordinator._receipt_service = service
    exact_coordinator._receipt_store = store
    object.__setattr__(factory, "_coordinator", exact_coordinator)
    conflicting = receipt._receipt(binding, 8, "b" * 64)
    assert conflicting is not None
    assert store.commit(conflicting).outcome == "committed"

    outcome = service._commit_consumed_r26_projection_v1(
        projection,
        factory,
        binding,
        repository=repository,
        composition=composition,
        coordinator=exact_coordinator,
        invocation_authority=invocation,
        receipt_store=store,
    )

    assert outcome.outcome == "CONFLICT"
    assert projection in r26._CONSUMED_RECEIPT_PROJECTIONS


def test_fresh_proof_confirms_exact_existing_receipt_after_restart_equivalent_replay(
    tmp_path: Path,
) -> None:
    service = receipt.DurableApplicationCommitReceiptService()
    store = receipt.LocalDurableApplicationCommitReceiptStore(tmp_path / "owner")

    class _Coordinator:
        pass

    coordinator = _Coordinator()
    coordinator._receipt_service = service
    coordinator._receipt_store = store
    first_factory, first_projection, binding, repository, composition, _, first_invocation = (
        _consume_projection()
    )
    object.__setattr__(first_factory, "_coordinator", coordinator)
    first = service._commit_consumed_r26_projection_v1(
        first_projection,
        first_factory,
        binding,
        repository=repository,
        composition=composition,
        coordinator=coordinator,
        invocation_authority=first_invocation,
        receipt_store=store,
    )
    assert first.outcome == "RECEIPT_CONFIRMED"

    factory, proof, same_binding, _, _, _ = _issued_proof(
        repository=repository, composition=composition, coordinator=coordinator
    )
    projection = r26._consume_r26_reconciliation_proof_into_receipt_projection_v1(
        proof, factory, same_binding, invocation_authority=proof._invocation
    ).projection
    assert projection is not None
    replay = service._commit_consumed_r26_projection_v1(
        projection,
        factory,
        same_binding,
        repository=repository,
        composition=composition,
        coordinator=coordinator,
        invocation_authority=proof._invocation,
        receipt_store=store,
    )

    assert replay.outcome == "RECEIPT_CONFIRMED"


def test_corrupt_readback_fails_closed_after_exact_receipt_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    factory, projection, binding, repository, composition, _, invocation = _consume_projection()
    service = receipt.DurableApplicationCommitReceiptService()
    store = receipt.LocalDurableApplicationCommitReceiptStore(tmp_path / "owner")

    class _Coordinator:
        pass

    exact_coordinator = _Coordinator()
    exact_coordinator._receipt_service = service
    exact_coordinator._receipt_store = store
    object.__setattr__(factory, "_coordinator", exact_coordinator)
    monkeypatch.setattr(
        store,
        "lookup_exact",
        lambda *_args: receipt.DurableApplicationCommitReceiptExactLookupResult("corrupt"),
    )

    outcome = service._commit_consumed_r26_projection_v1(
        projection,
        factory,
        binding,
        repository=repository,
        composition=composition,
        coordinator=exact_coordinator,
        invocation_authority=invocation,
        receipt_store=store,
    )

    assert outcome.outcome == "CORRUPT"
    assert projection in r26._CONSUMED_RECEIPT_PROJECTIONS


@pytest.mark.parametrize("count", [2, 8])
def test_concurrent_proof_consumption_has_one_projection_winner(count: int) -> None:
    factory, proof, binding, _, _, _ = _issued_proof()
    outcomes = _concurrent(
        count,
        lambda: r26._consume_r26_reconciliation_proof_into_receipt_projection_v1(
            proof, factory, binding, invocation_authority=proof._invocation
        ),
    )

    winners = [
        outcome for outcome in outcomes if outcome.outcome == "SEALED_RECONCILIATION_PROOF_ISSUED"
    ]
    assert len(winners) == 1
    assert winners[0].projection is not None
    assert [outcome.outcome for outcome in outcomes].count("CONSUMED") == count - 1
    assert proof not in r26._ISSUED
    assert proof in r26._CONSUMED
    assert len(r26._RECEIPT_PROJECTIONS) == 1


def test_repeated_concurrent_proof_consumption_never_duplicates_projection() -> None:
    for _ in range(12):
        factory, proof, binding, _, _, _ = _issued_proof()
        outcomes = _concurrent(
            8,
            lambda proof=proof, factory=factory, binding=binding: (
                r26._consume_r26_reconciliation_proof_into_receipt_projection_v1(
                    proof, factory, binding, invocation_authority=proof._invocation
                )
            ),
        )
        assert [outcome.outcome for outcome in outcomes].count(
            "SEALED_RECONCILIATION_PROOF_ISSUED"
        ) == 1
        assert [outcome.outcome for outcome in outcomes].count("CONSUMED") == 7
        assert proof not in r26._ISSUED


@pytest.mark.parametrize("count", [2, 8])
def test_concurrent_projection_consumption_has_one_receipt_winner(count: int) -> None:
    factory, projection, binding, repository, composition, coordinator, invocation = (
        _consume_projection()
    )
    outcomes = _concurrent(
        count,
        lambda: r26._consume_r26_receipt_projection_for_receipt_v1(
            projection,
            factory,
            binding,
            repository=repository,
            composition=composition,
            coordinator=coordinator,
            invocation_authority=invocation,
        ),
    )

    assert [outcome.outcome for outcome in outcomes].count(
        "SEALED_RECONCILIATION_PROOF_ISSUED"
    ) == 1
    assert [outcome.outcome for outcome in outcomes].count("CONSUMED") == count - 1
    assert projection not in r26._RECEIPT_PROJECTIONS
    assert projection in r26._CONSUMED_RECEIPT_PROJECTIONS


def test_repeated_concurrent_projection_consumption_never_duplicates_receipt_authority() -> None:
    for _ in range(12):
        factory, projection, binding, repository, composition, coordinator, invocation = (
            _consume_projection()
        )
        outcomes = _concurrent(
            8,
            lambda projection=projection, factory=factory, binding=binding, repository=repository, composition=composition, coordinator=coordinator, invocation=invocation: (
                r26._consume_r26_receipt_projection_for_receipt_v1(
                    projection,
                    factory,
                    binding,
                    repository=repository,
                    composition=composition,
                    coordinator=coordinator,
                    invocation_authority=invocation,
                )
            ),
        )
        assert [outcome.outcome for outcome in outcomes].count(
            "SEALED_RECONCILIATION_PROOF_ISSUED"
        ) == 1
        assert [outcome.outcome for outcome in outcomes].count("CONSUMED") == 7
        assert projection not in r26._RECEIPT_PROJECTIONS


@pytest.mark.parametrize("count", [2, 8])
def test_concurrent_confirmation_issuance_has_one_authoritative_lineage(
    tmp_path: Path, count: int
) -> None:
    coordinator, binding, composition, invocation, fence, context = _pending_receipt_confirmation(
        tmp_path, str(count)
    )
    factory = coordinator._r26_proof_factory
    confirmations = _concurrent(
        count,
        lambda: coordinator._issue_exact_receipt_reconciliation_confirmation_v1(
            factory, binding, composition, invocation
        ),
    )

    assert sum(confirmation is not None for confirmation in confirmations) == 1
    assert len(coordinator._r26_receipt_confirmations) == 1
    assert len(coordinator._r26_receipt_confirmation_records) == 1
    assert invocation not in coordinator._r26_pending_receipt_confirmations
    projection = next(
        projection
        for projection, facts in r26._CONSUMED_RECEIPT_PROJECTIONS.items()
        if facts[1] is invocation
    )
    assert not coordinator._record_r26_pending_receipt_confirmation_v1(
        factory, binding, composition, invocation, projection
    )
    assert (
        coordinator._issue_exact_receipt_reconciliation_confirmation_v1(
            factory, binding, composition, invocation
        )
        is None
    )
    assert len(coordinator._r26_receipt_confirmation_records) == 1
    winner = next(confirmation for confirmation in confirmations if confirmation is not None)
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        copy.copy(winner)
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        copy.deepcopy(winner)
    reconstructed = object.__new__(type(winner))
    assert reconstructed not in coordinator._r26_receipt_confirmation_records
    coordinator._r26_active_fence_contexts.discard(context)
    fence.release()


def test_terminal_confirmation_is_isolated_to_its_exact_invocation(
    tmp_path: Path,
) -> None:
    first_coordinator, first_binding, first_composition, first_invocation, first_fence, first_context = (
        _pending_receipt_confirmation(tmp_path, "terminal-first")
    )
    first_confirmation = first_coordinator._issue_exact_receipt_reconciliation_confirmation_v1(
        first_coordinator._r26_proof_factory,
        first_binding,
        first_composition,
        first_invocation,
    )
    assert first_confirmation is not None
    first_coordinator._r26_active_fence_contexts.discard(first_context)
    first_fence.release()

    second_coordinator, second_binding, second_composition, second_invocation, second_fence, second_context = (
        _pending_receipt_confirmation(tmp_path, "terminal-second")
    )
    second_confirmation = second_coordinator._issue_exact_receipt_reconciliation_confirmation_v1(
        second_coordinator._r26_proof_factory,
        second_binding,
        second_composition,
        second_invocation,
    )
    assert second_confirmation is not None
    assert first_confirmation is not second_confirmation
    assert len(first_coordinator._r26_receipt_confirmation_records) == 1
    assert len(second_coordinator._r26_receipt_confirmation_records) == 1

    second_coordinator._r26_active_fence_contexts.discard(second_context)
    second_fence.release()


def test_repeated_concurrent_confirmation_issuance_never_duplicates_lineage(tmp_path: Path) -> None:
    for index in range(8):
        coordinator, binding, composition, invocation, fence, context = _pending_receipt_confirmation(
            tmp_path.parent, f"stress-{index}"
        )
        factory = coordinator._r26_proof_factory
        confirmations = _concurrent(
            8,
            lambda coordinator=coordinator, factory=factory, binding=binding, composition=composition, invocation=invocation: (
                coordinator._issue_exact_receipt_reconciliation_confirmation_v1(
                    factory, binding, composition, invocation
                )
            ),
        )
        assert sum(confirmation is not None for confirmation in confirmations) == 1
        assert len(coordinator._r26_receipt_confirmations) == 1
        assert len(coordinator._r26_receipt_confirmation_records) == 1
        coordinator._r26_active_fence_contexts.discard(context)
        fence.release()
