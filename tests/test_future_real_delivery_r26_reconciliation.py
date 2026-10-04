from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace

import pytest

from manga_director.domain.state_machine import PageState
from manga_director.production import future_real_delivery_r26_reconciliation as r26
from manga_director.production import next_generation_workflow_application_ledger as ledger
from manga_director.production.future_real_delivery_binding_authority import _BindingReplayFailureV1
from manga_director.production.future_real_delivery_r25_attestation import (
    _canonical_r25_record_v1,
    _R25CanonicalRecordV1,
    _R25ReplayFailureV1,
)
from manga_director.production.future_real_delivery_r25_trusted_pairing import (
    _R20ReplayFailureV1,
    _r27_application_binding_identity,
    _r27_application_binding_json,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    WorkflowApplicationLedgerBindingDTO,
    _R26ProtocolObservationV2,
)
from manga_director.workflow import localfile_private_real_delivery_composition as private
from manga_director.workflow.contracts import WorkflowContext
from manga_director.workflow.localfile_external_generated_application import (
    _ExternalApplicationFenceContext,
    _R26FenceInvocationAuthorityV1,
)
from manga_director.workflow.page_execution_fence import WindowsPageExecutionFence


@pytest.fixture(autouse=True)
def _clear_private_registries() -> None:
    with private._REGISTRY_LOCK:
        private._ROOTS_BY_REPOSITORY.clear()
        private._REPOSITORY_BY_DURABLE_ROOT.clear()
    with ledger._R26_CAPABILITY_LOCK:
        ledger._R26_READY_ROOTS.clear()
    ledger._R26_PREPARATION_CAPABILITIES.clear()
    ledger._R26_OBSERVATION_CAPABILITIES.clear()
    ledger._R26_AUTHENTICATED_OBSERVATIONS.clear()
    r26._FACTORIES.clear()
    r26._ROOT_FACTORIES.clear()
    r26._ISSUED.clear()
    r26._CONSUMED.clear()
    r26._PROOFS_BY_INVOCATION.clear()


def _binding(suffix: str = "one") -> WorkflowApplicationLedgerBindingDTO:
    return WorkflowApplicationLedgerBindingDTO(
        attempt_id=f"attempt-{suffix}",
        authorization_id=f"authorization-{suffix}",
        project_id="project-1",
        page_id="page-1",
        target_page_reference="page-1",
        provider_reference=f"provider-{suffix}",
        output_asset_id=f"asset-{suffix}",
        source_state="PromptBuilt",
        target_state="Generated",
    )


def _ready_root(tmp_path: Path) -> object:
    tmp_path.mkdir(parents=True, exist_ok=True)
    return private._create_private_real_delivery_workflow_host_v1(
        tmp_path
    )._start_private_real_delivery_composition_v1()


def _fence_authority(
    root: object, binding: WorkflowApplicationLedgerBindingDTO
) -> tuple[object, WindowsPageExecutionFence, _ExternalApplicationFenceContext]:
    coordinator = root._composition.external_application
    fence = WindowsPageExecutionFence(binding.project_id, binding.page_id)
    fence.acquire()
    context = _ExternalApplicationFenceContext._create(
        binding, SimpleNamespace(revision=1, fingerprint="a" * 64)
    )
    coordinator._r26_active_fence_contexts.add(context)
    authority = coordinator._issue_r26_fence_invocation_authority_v1(binding, fence, context)
    return authority, fence, context


def _release_fence_authority(
    root: object,
    authority: object,
    fence: WindowsPageExecutionFence,
    context: _ExternalApplicationFenceContext,
) -> None:
    coordinator = root._composition.external_application
    coordinator._tombstone_r26_fence_invocation_authority_v1(authority)
    coordinator._r26_active_fence_contexts.discard(context)
    fence.release()


def _issue(
    root: object,
    observation: object,
    binding: WorkflowApplicationLedgerBindingDTO | None = None,
) -> r26._R26ProofIssuanceResultV1:
    factory = root._r26_proof_factory
    coordinator = root._composition.external_application
    binding = _binding() if binding is None else binding
    authority, fence, context = _fence_authority(root, binding)
    try:
        return r26._issue_r26_reconciliation_proof_under_fence(
            factory,
            binding,
            observation,
            coordinator=coordinator,
            page_store=coordinator._page_store,
            invocation_authority=authority,
        )
    finally:
        _release_fence_authority(root, authority, fence, context)


def _exact_record(
    binding: WorkflowApplicationLedgerBindingDTO,
    r20: SimpleNamespace,
    *,
    delivery_identity: str | None = None,
    pre_commit_revision: int | None = None,
    pre_commit_fingerprint: str | None = None,
) -> _R25CanonicalRecordV1:
    return _canonical_r25_record_v1(
        delivery_identity=r20.delivery_identity if delivery_identity is None else delivery_identity,
        attempt_id=binding.attempt_id,
        application_binding_digest=_r27_application_binding_identity(binding),
        project_id=binding.project_id,
        page_id=binding.page_id,
        target_page_reference=binding.target_page_reference,
        provider_reference=binding.provider_reference,
        authorization_id=binding.authorization_id,
        output_asset_id=binding.output_asset_id,
        canonical_result_identity=r20.canonical_result_identity,
        logical_output_id=r20.logical_output_id,
        asset_identity=r20.asset_id,
        asset_sha256=r20.asset_sha256,
        expected_byte_length=r20.expected_byte_length,
        evidence_identity=r20.evidence_identity,
        evidence_persistence_digest=r20.evidence_persistence_identity,
        evidence_binding_fingerprint=r20.binding_digest,
        pre_commit_revision=(
            r20.historical_page_revision if pre_commit_revision is None else pre_commit_revision
        ),
        pre_commit_fingerprint=(
            r20.historical_page_fingerprint
            if pre_commit_fingerprint is None
            else pre_commit_fingerprint
        ),
        post_commit_revision=7,
        post_commit_fingerprint="f" * 64,
        application_binding_json=_r27_application_binding_json(binding),
    )


def _exact_r20_facts(binding: WorkflowApplicationLedgerBindingDTO) -> SimpleNamespace:
    return SimpleNamespace(
        delivery_identity="1" * 64,
        canonical_result_identity="canonical-result",
        logical_output_id=binding.output_asset_id,
        asset_id="asset-id",
        asset_sha256="a" * 64,
        expected_byte_length=128,
        media_type="image/png",
        evidence_identity="e" * 64,
        evidence_persistence_identity="b" * 64,
        binding_digest="c" * 64,
        historical_page_revision=1,
        historical_page_fingerprint="d" * 64,
    )


def _patch_exact_predecessors(
    root: object,
    binding: WorkflowApplicationLedgerBindingDTO,
    monkeypatch: pytest.MonkeyPatch,
    context: WorkflowContext,
    *,
    r20: SimpleNamespace | None = None,
    record: _R25CanonicalRecordV1 | None = None,
) -> object:
    factory = root._r26_proof_factory
    coordinator = root._composition.external_application
    exact_r20 = _exact_r20_facts(binding) if r20 is None else r20
    exact_record = _exact_record(binding, exact_r20) if record is None else record
    page_store_type = type(coordinator._page_store)
    r20_reader_type = type(factory._r25._r20_reader)
    r25_store_type = type(factory._r25._r25_store)
    monkeypatch.setattr(r20_reader_type, "_replay_for_binding_v1", lambda _self, _binding: exact_r20)
    monkeypatch.setattr(
        r25_store_type,
        "_replay_post_cas_attestation_exact_v1",
        lambda _self, _binding_digest: exact_record,
    )
    monkeypatch.setattr(
        page_store_type,
        "load_revisioned",
        lambda _self, _project_id: SimpleNamespace(revision=7, fingerprint="f" * 64),
    )
    monkeypatch.setattr(page_store_type, "context_from_snapshot", lambda _self, _snapshot, _page_id: context)
    return factory


def _exact_generated_context(binding: WorkflowApplicationLedgerBindingDTO) -> WorkflowContext:
    return WorkflowContext(
        page={"project_id": binding.project_id, "page_id": binding.page_id},
        state=PageState.GENERATED,
        artifacts={
            PageState.GENERATED.value: {
                "artifact_kind": "logical_output_asset",
                "output_asset_id": binding.output_asset_id,
            }
        },
    )


@pytest.mark.parametrize(
    ("r20_media_type", "record_updates"),
    [
        ("image/png", {"delivery_identity": "2" * 64}),
        ("image/jpeg", {}),
        ("image/png", {"pre_commit_revision": 2}),
        ("image/png", {"pre_commit_fingerprint": "3" * 64}),
    ],
    ids=("delivery-identity", "media-type", "pre-commit-revision", "pre-commit-fingerprint"),
)
def test_r26_rejects_each_r25_r20_cross_binding_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    r20_media_type: str,
    record_updates: dict[str, str | int],
) -> None:
    root = _ready_root(tmp_path)
    binding = _binding()
    assert root._prepare_r26_protocol_marker_v1(binding).outcome == "prepared"
    r20 = _exact_r20_facts(binding)
    r20.media_type = r20_media_type
    record = _exact_record(binding, r20, **record_updates)
    _patch_exact_predecessors(
        root,
        binding,
        monkeypatch,
        _exact_generated_context(binding),
        r20=r20,
        record=record,
    )

    result = _issue(root, root._observe_r26_protocol_marker_v2(binding), binding)

    assert result.outcome == "CONFLICT"
    assert result.proof is None


def test_r26_rejects_combined_r25_r20_cross_binding_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _ready_root(tmp_path)
    binding = _binding()
    assert root._prepare_r26_protocol_marker_v1(binding).outcome == "prepared"
    r20 = _exact_r20_facts(binding)
    r20.media_type = "image/jpeg"
    record = _exact_record(
        binding,
        r20,
        delivery_identity="2" * 64,
        pre_commit_revision=2,
        pre_commit_fingerprint="3" * 64,
    )
    _patch_exact_predecessors(
        root,
        binding,
        monkeypatch,
        _exact_generated_context(binding),
        r20=r20,
        record=record,
    )

    result = _issue(root, root._observe_r26_protocol_marker_v2(binding), binding)

    assert result.outcome == "CONFLICT"
    assert result.proof is None


def test_r26_issues_proof_for_exact_canonical_r25_r20_cross_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _ready_root(tmp_path)
    binding = _binding()
    assert root._prepare_r26_protocol_marker_v1(binding).outcome == "prepared"
    r20 = _exact_r20_facts(binding)
    record = _exact_record(binding, r20)
    _patch_exact_predecessors(
        root,
        binding,
        monkeypatch,
        _exact_generated_context(binding),
        r20=r20,
        record=record,
    )

    result = _issue(root, root._observe_r26_protocol_marker_v2(binding), binding)

    assert result.outcome == "SEALED_RECONCILIATION_PROOF_ISSUED"
    assert result.proof is not None


def test_private_ready_root_attaches_one_exact_r26_factory(tmp_path: Path) -> None:
    root = _ready_root(tmp_path)
    factory = root._r26_proof_factory

    assert type(factory) is r26._R26ReconciliationProofFactoryV1
    assert r26._FACTORIES[factory][0] is root
    assert r26._FACTORIES[factory][1] is root._repository
    assert r26._FACTORIES[factory][2] is root._composition.external_application
    assert root._composition.external_application._r26_proof_factory is factory


def test_exact_ready_root_cannot_be_rebound_to_a_second_factory(tmp_path: Path) -> None:
    root = _ready_root(tmp_path)
    coordinator = root._composition.external_application

    rebound = r26._construct_r26_reconciliation_proof_factory_v1(
        root,
        root._repository,
        coordinator,
        coordinator._page_store,
        root._ledger_store,
        coordinator._r25_localfile_composition,
        _issuer=r26._R26_PROOF_FACTORY_ISSUER,
    )

    assert rebound is root._r26_proof_factory
    assert len(r26._ROOT_FACTORIES) == 1


def test_factory_construction_rejects_direct_or_cross_composition_inputs(tmp_path: Path) -> None:
    root = _ready_root(tmp_path)
    coordinator = root._composition.external_application

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        r26._R26ReconciliationProofFactoryV1()
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        r26._construct_r26_reconciliation_proof_factory_v1(
            root,
            root._repository,
            coordinator,
            coordinator._page_store,
            root._ledger_store,
            coordinator._r25_localfile_composition,
            _issuer=object(),
        )
    assert (
        r26._issue_r26_reconciliation_proof_under_fence(
            root._r26_proof_factory,
            _binding(),
            _R26ProtocolObservationV2("APPLIED"),
            coordinator=object(),
            page_store=coordinator._page_store,
            invocation_authority=object(),
        ).outcome
        == "AUTHORITY_REJECTED"
    )


@pytest.mark.parametrize(
    ("observation", "expected"),
    [
        (_R26ProtocolObservationV2("APPLIED"), "ALREADY_APPLIED"),
        (_R26ProtocolObservationV2("MISSING"), "RECOVERY_REQUIRED"),
        (_R26ProtocolObservationV2("RECOVERY_REQUIRED"), "RECOVERY_REQUIRED"),
        (_R26ProtocolObservationV2("CORRUPT"), "CORRUPT"),
        (_R26ProtocolObservationV2("CONFLICT"), "CONFLICT"),
        (_R26ProtocolObservationV2("AUTHORITY_REJECTED"), "AUTHORITY_REJECTED"),
        (_R26ProtocolObservationV2("PREPARED", 0, "legacy"), "LEGACY_PRE_ATTESTATION"),
        (_R26ProtocolObservationV2("PREPARED", 1, "wrong"), "CORRUPT"),
    ],
)
def test_r21_observation_outcomes_have_one_fail_closed_r26_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    observation: _R26ProtocolObservationV2,
    expected: str,
) -> None:
    root = _ready_root(tmp_path)
    binding = _binding()
    store_type = type(root._ledger_store)
    monkeypatch.setattr(
        store_type, "_observe_r26_protocol_exact_readonly_v2", lambda *_args, **_kwargs: observation
    )
    source = root._observe_r26_protocol_marker_v2(binding)
    assert _issue(root, source, binding).outcome == expected


def test_exact_marker_observation_still_requires_readonly_r20_and_r25_facts(tmp_path: Path) -> None:
    root = _ready_root(tmp_path)
    binding = _binding()
    assert root._prepare_r26_protocol_marker_v1(binding).outcome == "prepared"

    result = _issue(root, root._observe_r26_protocol_marker_v2(binding), binding)

    assert result.outcome == "RECOVERY_REQUIRED"
    assert result.proof is None
    assert not r26._ISSUED


@pytest.mark.parametrize(
    ("source_outcome", "expected"),
    [
        ("NOT_FOUND", "RECOVERY_REQUIRED"),
        ("RECOVERY_REQUIRED", "RECOVERY_REQUIRED"),
        ("CORRUPT", "CORRUPT"),
        ("CONFLICT", "CONFLICT"),
    ],
)
def test_r20_readonly_failure_matrix_is_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source_outcome: str, expected: str
) -> None:
    root = _ready_root(tmp_path)
    binding = _binding()
    assert root._prepare_r26_protocol_marker_v1(binding).outcome == "prepared"
    reader_type = type(root._r26_proof_factory._r25._r20_reader)

    def fail_r20(_self: object, _binding: object) -> object:
        raise _R20ReplayFailureV1(source_outcome)  # type: ignore[arg-type]

    monkeypatch.setattr(reader_type, "_replay_for_binding_v1", fail_r20)
    assert _issue(root, root._observe_r26_protocol_marker_v2(binding), binding).outcome == expected


@pytest.mark.parametrize(
    ("source_outcome", "expected"),
    [
        ("NOT_FOUND", "RECOVERY_REQUIRED"),
        ("RECOVERY_REQUIRED", "RECOVERY_REQUIRED"),
        ("CORRUPT", "CORRUPT"),
        ("CONFLICT", "CONFLICT"),
        ("AUTHORITY_REJECTED", "AUTHORITY_REJECTED"),
    ],
)
def test_r25_readonly_failure_matrix_is_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, source_outcome: str, expected: str
) -> None:
    root = _ready_root(tmp_path)
    binding = _binding()
    assert root._prepare_r26_protocol_marker_v1(binding).outcome == "prepared"
    r25 = root._r26_proof_factory._r25
    reader_type = type(r25._r20_reader)
    store_type = type(r25._r25_store)
    monkeypatch.setattr(
        reader_type,
        "_replay_for_binding_v1",
        lambda _self, _binding: SimpleNamespace(),
    )

    def fail_r25(_self: object, _binding_digest: object) -> object:
        raise _R25ReplayFailureV1(source_outcome)  # type: ignore[arg-type]

    monkeypatch.setattr(store_type, "_replay_post_cas_attestation_exact_v1", fail_r25)
    assert _issue(root, root._observe_r26_protocol_marker_v2(binding), binding).outcome == expected


def test_r26_taxonomy_is_not_derived_from_predecessor_exception_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _ready_root(tmp_path)
    binding = _binding()
    assert root._prepare_r26_protocol_marker_v1(binding).outcome == "prepared"
    reader_type = type(root._r26_proof_factory._r25._r20_reader)

    def value_error_named_like_an_authority_failure(_self: object, _binding: object) -> object:
        raise ValueError("AUTHORITY_REJECTED")

    monkeypatch.setattr(reader_type, "_replay_for_binding_v1", value_error_named_like_an_authority_failure)
    assert _issue(root, root._observe_r26_protocol_marker_v2(binding), binding).outcome == "CORRUPT"


@pytest.mark.parametrize(
    ("outcome", "diagnostic", "expected"),
    (
        ("CORRUPT", "AUTHORITY_REJECTED", "CORRUPT"),
        ("RECOVERY_REQUIRED", "CORRUPT", "RECOVERY_REQUIRED"),
    ),
)
def test_r18_r20_r26_taxonomy_uses_structured_owner_failure_origin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
    diagnostic: str,
    expected: str,
) -> None:
    root = _ready_root(tmp_path)
    binding = _binding()
    assert root._prepare_r26_protocol_marker_v1(binding).outcome == "prepared"
    authority_type = type(root._r26_proof_factory._r25._r20_reader._authority)

    def structured_owner_failure(_self: object, _attempt_id: object) -> object:
        error = _BindingReplayFailureV1(outcome)  # type: ignore[arg-type]
        error.args = (diagnostic,)
        raise error

    monkeypatch.setattr(
        authority_type, "_replay_historical_binding_for_attempt_v1", structured_owner_failure
    )

    assert _issue(root, root._observe_r26_protocol_marker_v2(binding), binding).outcome == expected


def test_r26_allows_only_one_live_invocation_authority_per_exact_context(tmp_path: Path) -> None:
    root = _ready_root(tmp_path)
    binding = _binding()
    coordinator = root._composition.external_application
    authority, fence, context = _fence_authority(root, binding)
    try:
        with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
            coordinator._issue_r26_fence_invocation_authority_v1(binding, fence, context)
        assert coordinator._r26_fence_invocations_by_context[context] is authority
        assert coordinator._r26_fence_invocations == {authority}
    finally:
        _release_fence_authority(root, authority, fence, context)

    replacement, next_fence, next_context = _fence_authority(root, binding)
    try:
        assert replacement is not authority
        assert coordinator._r26_fence_invocations_by_context[next_context] is replacement
    finally:
        _release_fence_authority(root, replacement, next_fence, next_context)


def test_reconstructed_copied_and_deepcopied_proofs_are_not_consumable(tmp_path: Path) -> None:
    root = _ready_root(tmp_path)
    factory = root._r26_proof_factory
    binding = _binding()
    forged = object.__new__(r26._AuthoritativePostCASReconciliationProofV1)
    assert (
        r26._consume_r26_reconciliation_proof_for_receipt_v1(
            forged, factory, binding, invocation_authority=object()
        )
        == "AUTHORITY_REJECTED"
    )
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        copy.copy(forged)
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        copy.deepcopy(forged)


def test_non_r26_objects_cannot_be_consumed_as_proofs(tmp_path: Path) -> None:
    root = _ready_root(tmp_path)
    assert (
        r26._consume_r26_reconciliation_proof_for_receipt_v1(
            object(), root._r26_proof_factory, _binding(), invocation_authority=object()
        )
        == "AUTHORITY_REJECTED"
    )


def test_r26_rejects_reconstructed_or_consumed_invocation_authority(tmp_path: Path) -> None:
    root = _ready_root(tmp_path)
    binding = _binding()
    source = root._observe_r26_protocol_marker_v2(binding)
    coordinator = root._composition.external_application
    factory = root._r26_proof_factory
    forged = object.__new__(_R26FenceInvocationAuthorityV1)

    assert (
        r26._issue_r26_reconciliation_proof_under_fence(
            factory,
            binding,
            source,
            coordinator=coordinator,
            page_store=coordinator._page_store,
            invocation_authority=forged,
        ).outcome
        == "AUTHORITY_REJECTED"
    )

    authority, fence, context = _fence_authority(root, binding)
    try:
        with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
            copy.copy(authority)
        with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
            copy.deepcopy(authority)
        assert (
            r26._issue_r26_reconciliation_proof_under_fence(
                factory,
                binding,
                _R26ProtocolObservationV2("PREPARED", 1, "valid-looking"),
                coordinator=coordinator,
                page_store=coordinator._page_store,
                invocation_authority=authority,
            ).outcome
            == "AUTHORITY_REJECTED"
        )
        assert (
            r26._issue_r26_reconciliation_proof_under_fence(
                factory,
                binding,
                source,
                coordinator=coordinator,
                page_store=coordinator._page_store,
                invocation_authority=authority,
            ).outcome
            == "AUTHORITY_REJECTED"
        )
    finally:
        _release_fence_authority(root, authority, fence, context)


def test_r26_invocation_and_fence_cross_binding_are_rejected(tmp_path: Path) -> None:
    root = _ready_root(tmp_path)
    binding = _binding()
    foreign_binding = WorkflowApplicationLedgerBindingDTO(
        attempt_id=binding.attempt_id,
        authorization_id=binding.authorization_id,
        project_id=binding.project_id,
        page_id="page-2",
        target_page_reference="page-2",
        provider_reference=binding.provider_reference,
        output_asset_id=binding.output_asset_id,
        source_state=binding.source_state,
        target_state=binding.target_state,
    )
    coordinator = root._composition.external_application
    source = root._observe_r26_protocol_marker_v2(binding)
    authority, fence, context = _fence_authority(root, foreign_binding)
    try:
        assert (
            r26._issue_r26_reconciliation_proof_under_fence(
                root._r26_proof_factory,
                binding,
                source,
                coordinator=coordinator,
                page_store=coordinator._page_store,
                invocation_authority=authority,
            ).outcome
            == "AUTHORITY_REJECTED"
        )
    finally:
        _release_fence_authority(root, authority, fence, context)


def test_r26_rejects_foreign_coordinator_invocation_authority(tmp_path: Path) -> None:
    root = _ready_root(tmp_path)
    binding = _binding()
    source = root._observe_r26_protocol_marker_v2(binding)
    authority, fence, context = _fence_authority(root, binding)
    try:
        coordinator = root._composition.external_application
        assert (
            r26._issue_r26_reconciliation_proof_under_fence(
                root._r26_proof_factory,
                binding,
                source,
                coordinator=object(),
                page_store=coordinator._page_store,
                invocation_authority=authority,
            ).outcome
            == "AUTHORITY_REJECTED"
        )
    finally:
        _release_fence_authority(root, authority, fence, context)


def test_r26_authenticated_observation_rejects_copy_and_value_reconstruction(tmp_path: Path) -> None:
    root = _ready_root(tmp_path)
    binding = _binding()
    source = root._observe_r26_protocol_marker_v2(binding)
    assert type(source).__name__ == "_R26AuthenticatedProtocolObservationV1"
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        copy.copy(source)
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        copy.deepcopy(source)

    reconstructed = _R26ProtocolObservationV2(
        source.outcome, source.marker_version, source.protocol_binding_digest
    )
    assert _issue(root, reconstructed, binding).outcome == "AUTHORITY_REJECTED"


def test_r26_rejects_authenticated_observation_from_foreign_ready_root(tmp_path: Path) -> None:
    root = _ready_root(tmp_path)
    binding = _binding()
    foreign_source = object.__new__(ledger._R26AuthenticatedProtocolObservationV1)

    assert _issue(root, foreign_source, binding).outcome == "AUTHORITY_REJECTED"


def test_r26_authenticated_observation_is_one_shot_after_exact_readonly_use(tmp_path: Path) -> None:
    root = _ready_root(tmp_path)
    binding = _binding()
    source = root._observe_r26_protocol_marker_v2(binding)

    assert _issue(root, source, binding).outcome != "AUTHORITY_REJECTED"
    assert _issue(root, source, binding).outcome == "AUTHORITY_REJECTED"


def test_exact_proof_is_one_shot_and_carries_the_exact_factory_nonce(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _ready_root(tmp_path)
    coordinator = root._composition.external_application
    binding = _binding()
    assert root._prepare_r26_protocol_marker_v1(binding).outcome == "prepared"
    observation = root._observe_r26_protocol_marker_v2(binding)
    factory = _patch_exact_predecessors(
        root,
        binding,
        monkeypatch,
        WorkflowContext(
            page={"project_id": binding.project_id, "page_id": binding.page_id},
            state=PageState.GENERATED,
            artifacts={
                PageState.GENERATED.value: {
                    "artifact_kind": "logical_output_asset",
                    "output_asset_id": binding.output_asset_id,
                }
            },
        ),
    )
    authority, fence, context = _fence_authority(root, binding)
    try:
        issued = r26._issue_r26_reconciliation_proof_under_fence(
            factory,
            binding,
            observation,
            coordinator=coordinator,
            page_store=coordinator._page_store,
            invocation_authority=authority,
        )

        assert issued.outcome == "SEALED_RECONCILIATION_PROOF_ISSUED"
        assert issued.proof is not None
        assert issued.proof._nonce is factory._nonce
        second_observation = root._observe_r26_protocol_marker_v2(binding)
        duplicate = r26._issue_r26_reconciliation_proof_under_fence(
            factory,
            binding,
            second_observation,
            coordinator=coordinator,
            page_store=coordinator._page_store,
            invocation_authority=authority,
        )
        assert duplicate.outcome == "AUTHORITY_REJECTED"
        assert tuple(r26._ISSUED) == (issued.proof,)
        assert (
            r26._consume_r26_reconciliation_proof_for_receipt_v1(
                issued.proof, factory, binding, invocation_authority=authority
            )
            == "SEALED_RECONCILIATION_PROOF_ISSUED"
        )
        assert (
            r26._consume_r26_reconciliation_proof_for_receipt_v1(
                issued.proof, factory, binding, invocation_authority=authority
            )
            == "CONSUMED"
        )
    finally:
        _release_fence_authority(root, authority, fence, context)


@pytest.mark.parametrize(
    "artifact",
    [
        {"artifact_kind": "logical_output_asset", "output_asset_id": "other-asset"},
        {"artifact_kind": "unexpected", "output_asset_id": "asset-one"},
        {},
    ],
)
def test_r26_real_workflow_context_requires_the_exact_generated_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, artifact: dict[str, str]
) -> None:
    root = _ready_root(tmp_path)
    binding = _binding()
    assert root._prepare_r26_protocol_marker_v1(binding).outcome == "prepared"
    coordinator = root._composition.external_application
    factory = _patch_exact_predecessors(
        root,
        binding,
        monkeypatch,
        WorkflowContext(
            page={"project_id": binding.project_id, "page_id": binding.page_id},
            state=PageState.GENERATED,
            artifacts={PageState.GENERATED.value: artifact},
        ),
    )
    authority, fence, context = _fence_authority(root, binding)
    try:
        result = r26._issue_r26_reconciliation_proof_under_fence(
            factory,
            binding,
            root._observe_r26_protocol_marker_v2(binding),
            coordinator=coordinator,
            page_store=coordinator._page_store,
            invocation_authority=authority,
        )
        assert result.outcome == "RECOVERY_REQUIRED"
        assert result.proof is None
    finally:
        _release_fence_authority(root, authority, fence, context)
