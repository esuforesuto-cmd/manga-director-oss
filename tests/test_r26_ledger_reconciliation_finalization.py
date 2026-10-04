"""Focused IMP-10 coverage for the sealed R26 Ledger finalizer."""

from __future__ import annotations

import copy
import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace

import pytest

from manga_director.domain.events import EventType, WorkflowEvent
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.production import (
    future_real_delivery_i02_real_asset_delivery_journal as i02_journal,
)
from manga_director.production import future_real_delivery_i02a_protocol as i02_protocol
from manga_director.production import next_generation_workflow_application_ledger as ledger
from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    DurableEvidenceWorkflowBindingReport,
    WorkflowApplicationAuthorizationDTO,
)
from manga_director.production.next_generation_generation_evidence import (
    EvidenceValueDTO,
    GenerationConfigurationEvidenceDTO,
    GenerationEvidenceEnvelopeDTO,
    GenerationInputEvidenceDTO,
    GenerationOutputEvidenceDTO,
)
from manga_director.production.next_generation_generation_evidence_persistence import (
    GenerationEvidenceStoreWriteRequest,
    LocalGenerationEvidenceStore,
)
from manga_director.production.next_generation_local_durable_asset_owner import (
    OwnerRegistrationMaterial,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    WorkflowApplicationLedgerBindingDTO,
)
from manga_director.workflow import localfile_external_generated_application as external
from manga_director.workflow import localfile_private_real_delivery_composition as private
from manga_director.workflow.page_execution_fence import WindowsPageExecutionFence

_PATH_A_IMAGE_BYTES = b"\x89PNG\r\n\x1a\n" + b"r26-finalizer-path-a" * 32
_PATH_A_IMAGE_DIGEST = hashlib.sha256(_PATH_A_IMAGE_BYTES).hexdigest()
_PATH_A_PROJECT_ID = "project-r26-finalizer-path-a"
_PATH_A_ATTEMPT_ID = "attempt:r26:finalizer:path-a"
_PATH_A_PROVIDER = "provider:r26:finalizer:path-a"
_PATH_A_OUTPUT = "output:r26:finalizer:path-a"
_PATH_A_TARGET = "target:r26:finalizer:path-a"


def _binding(suffix: str = "one") -> WorkflowApplicationLedgerBindingDTO:
    return WorkflowApplicationLedgerBindingDTO(
        attempt_id=f"attempt-{suffix}",
        authorization_id=f"authorization-{suffix}",
        project_id=f"project-{suffix}",
        page_id=f"page-{suffix}",
        target_page_reference=f"page-{suffix}",
        provider_reference=f"provider-{suffix}",
        output_asset_id=f"asset-{suffix}",
        source_state="PromptBuilt",
        target_state="Generated",
    )


def _ready_finalizer(
    tmp_path: Path, suffix: str = "one"
) -> tuple[object, object, object, WorkflowApplicationLedgerBindingDTO]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    root = private._create_private_real_delivery_workflow_host_v1(
        tmp_path / suffix
    )._start_private_real_delivery_composition_v1()
    binding = _binding(suffix)
    assert root._prepare_r26_protocol_marker_v1(binding).outcome == "prepared"
    observation = root._observe_r26_protocol_marker_v2(binding)
    coordinator = root._composition.external_application
    return coordinator._r26_ledger_finalizer_authorization, observation, root, binding


def _live_confirmation(
    tmp_path: Path, suffix: str
) -> tuple[
    object,
    object,
    WorkflowApplicationLedgerBindingDTO,
    object,
    WindowsPageExecutionFence,
    object,
    object,
]:
    """Build only the exact private state consumed by the Coordinator seam."""

    root = private._create_private_real_delivery_workflow_host_v1(
        tmp_path / suffix
    )._start_private_real_delivery_composition_v1()
    coordinator = root._composition.external_application
    binding = _binding(suffix)
    fence = WindowsPageExecutionFence(binding.project_id, binding.page_id)
    fence.acquire()
    context = external._ExternalApplicationFenceContext._create(
        binding, SimpleNamespace(revision=7, fingerprint="a" * 64)
    )
    coordinator._r26_active_fence_contexts.add(context)
    invocation = coordinator._issue_r26_fence_invocation_authority_v1(
        binding, fence, context
    )
    coordinator._r26_fence_invocations.discard(invocation)
    coordinator._r26_fence_invocations_by_context.pop(context, None)
    object.__setattr__(invocation, "_used", True)
    confirmation = object.__new__(external._ExactReceiptReconciliationConfirmationV1)
    seal = object()
    object.__setattr__(confirmation, "_seal", seal)
    factory = coordinator._r26_proof_factory
    coordinator._r26_receipt_confirmation_records[confirmation] = (
        coordinator,
        factory,
        root._repository,
        coordinator._r25_localfile_composition,
        invocation,
        binding,
        "b" * 64,
        7,
        "a" * 64,
        "c" * 64,
        confirmation,
        seal,
    )
    coordinator._r26_receipt_confirmations.add(confirmation)
    return coordinator, confirmation, binding, invocation, fence, context, root


def _release_confirmation_context(
    coordinator: object, context: object, fence: WindowsPageExecutionFence
) -> None:
    coordinator._r26_active_fence_contexts.discard(context)
    fence.release()


def _path_a_known(value: str) -> EvidenceValueDTO:
    return EvidenceValueDTO(availability="known", value=value)


def _path_a_binding_input() -> i02_journal._DeliveryBindingInputV1:
    return i02_journal._DeliveryBindingInputV1(
        attempt_id=_PATH_A_ATTEMPT_ID,
        project_id=_PATH_A_PROJECT_ID,
        page_id="1",
        target_page_reference=_PATH_A_TARGET,
        provider_reference=_PATH_A_PROVIDER,
        dispatch_identity="dispatch:r26:finalizer:path-a",
        idempotency_identity="idempotency:r26:finalizer:path-a",
        submission_receipt_identity="receipt:r26:finalizer:path-a",
        logical_output_id=_PATH_A_OUTPUT,
        canonical_result_identity=i02_journal._canonical_result_identity_v1(
            attempt_id=_PATH_A_ATTEMPT_ID,
            project_id=_PATH_A_PROJECT_ID,
            page_id="1",
            target_page_reference=_PATH_A_TARGET,
            provider_reference=_PATH_A_PROVIDER,
            dispatch_identity="dispatch:r26:finalizer:path-a",
            idempotency_identity="idempotency:r26:finalizer:path-a",
            submission_receipt_identity="receipt:r26:finalizer:path-a",
            logical_output_id=_PATH_A_OUTPUT,
            asset_sha256=_PATH_A_IMAGE_DIGEST,
            expected_byte_length=len(_PATH_A_IMAGE_BYTES),
        ),
        asset_sha256=_PATH_A_IMAGE_DIGEST,
        expected_byte_length=len(_PATH_A_IMAGE_BYTES),
    )


def _path_a_report() -> DurableEvidenceWorkflowBindingReport:
    return DurableEvidenceWorkflowBindingReport.model_validate(
        {
            "attempt_id": _PATH_A_ATTEMPT_ID,
            "provider_reference": _PATH_A_PROVIDER,
            "output_asset_id": _PATH_A_OUTPUT,
            "project_id": _PATH_A_PROJECT_ID,
            "page_id": "1",
            "target_page_reference": _PATH_A_TARGET,
            "status": "eligible",
            "eligible": True,
        }
    )


def _path_a_authorization() -> WorkflowApplicationAuthorizationDTO:
    return WorkflowApplicationAuthorizationDTO.model_validate(
        {
            "authorization_id": "authorization:r26:finalizer:path-a",
            "authorizer_id": "human:r26:finalizer:path-a",
            "authorized_at": datetime(2026, 9, 13, tzinfo=UTC),
            "attempt_id": _PATH_A_ATTEMPT_ID,
            "provider_reference": _PATH_A_PROVIDER,
            "project_id": _PATH_A_PROJECT_ID,
            "page_id": "1",
            "target_page_reference": _PATH_A_TARGET,
            "source_state": "PromptBuilt",
            "target_state": "Generated",
        }
    )


def _persist_path_a_completed_r18_history(root: object) -> None:
    """Persist the real R18/I02/evidence history through the host-owned R25 tuple."""

    composition = root._composition
    r25 = composition.external_application._r25_localfile_composition
    assert r25 is not None
    authority = r25._r18_authority
    binding = _path_a_binding_input()
    authority._journal._begin_delivery_v1(binding)
    authority._journal._record_bytes_validated_v1(
        binding.expected_byte_length, binding.asset_sha256, "image/png"
    )
    registration = authority._owner.register(
        OwnerRegistrationMaterial(
            attempt_id=binding.attempt_id,
            provider_reference=binding.provider_reference,
            image_bytes=_PATH_A_IMAGE_BYTES,
        )
    )
    assert registration.outcome == "registered"
    authority._journal._record_authenticated_asset_registered_v1(registration)
    state = i02_protocol._create_isolated_test_protocol_state_v1()
    bootstrap = state.take_bootstrap()
    bootstrap._register_production_journal_class_once_v1(i02_journal.PrivateRealAssetDeliveryJournal)
    journal_peer, verifier_peer = state.create_pair(authority._journal)
    request = journal_peer._issue_registered_owner_verification_request_v1()
    completion = verifier_peer._consume_request_and_issue_completion_v1(
        request,
        i02_protocol._VerifiedOwnerAssetFactsV1(
            assets_root_identity=("assets", 1, 2),
            final_file_identity=("asset.png", 1, 3, binding.expected_byte_length),
            verified_sha256=binding.asset_sha256,
            verified_byte_length=binding.expected_byte_length,
            verified_media_type="image/png",
            owner_attempt_id=binding.attempt_id,
            owner_provider_reference=binding.provider_reference,
            owner_digest=binding.asset_sha256,
            owner_storage_name="a" * 32 + ".png",
        ),
    )
    assert verifier_peer._consume_completion_and_call_journal_v1(completion) is (
        i02_protocol._JournalCompletionCallbackResultV1.COMMITTED
    )
    evidence = GenerationEvidenceEnvelopeDTO(
        attempt_id=_PATH_A_ATTEMPT_ID,
        observed_at=datetime(2026, 9, 13, tzinfo=UTC),
        provenance_reference="provenance:r26:finalizer:path-a",
        input=GenerationInputEvidenceDTO(input_reference="input:r26:finalizer:path-a"),
        output=GenerationOutputEvidenceDTO(
            output_asset_id=_PATH_A_OUTPUT,
            output_content_hash=_path_a_known(_PATH_A_IMAGE_DIGEST),
            media_type="image/png",
        ),
        configuration=GenerationConfigurationEvidenceDTO(
            provider_id=_path_a_known(_PATH_A_PROVIDER),
            model_id=_path_a_known("model:r26:finalizer:path-a"),
            model_version=_path_a_known("v1"),
            workflow_id=_path_a_known("workflow:r26:finalizer:path-a"),
            workflow_version=_path_a_known("v1"),
            seed=_path_a_known("42"),
        ),
    )
    evidence_store = LocalGenerationEvidenceStore(
        root._repository._next_generation_normal_execution_owner_root() / "evidence"
    )
    assert evidence_store.persist(
        GenerationEvidenceStoreWriteRequest(
            attempt_id=_PATH_A_ATTEMPT_ID,
            provider_reference=_PATH_A_PROVIDER,
            evidence_status="ready",
            generation_evidence=evidence,
        )
    ).outcome == "persisted"
    authority._create_exact_v1(binding.delivery_identity)


def _private_host_path_a_root(tmp_path: Path) -> object:
    root = private._create_private_real_delivery_workflow_host_v1(
        tmp_path / "private-host-path-a"
    )._start_private_real_delivery_composition_v1()
    root._repository.save(
        Project(
            id=_PATH_A_PROJECT_ID,
            title="R26 canonical finalizer Path A",
            pages=[
                Page(
                    page_number=1,
                    state=PageState.PROMPT_BUILT,
                    page_design={},
                    review={},
                    storyboard={"panels": [{"id": "panel:r26:finalizer:path-a"}]},
                    prompt={"positive": "R26 canonical finalizer Path A"},
                    metadata={"future_generation_target_reference": _PATH_A_TARGET},
                )
            ],
        )
    )
    _persist_path_a_completed_r18_history(root)
    return root


def test_private_host_canonical_path_a_finalizes_r26_after_actual_r27_cas(tmp_path: Path) -> None:
    """Exercise the actual private host restart path without synthetic R26 authority."""

    root = _private_host_path_a_root(tmp_path)
    composition = root._composition
    coordinator = composition.external_application
    assert coordinator._page_store._repository is root._repository
    assert coordinator._r26_proof_factory is root._r26_proof_factory
    assert coordinator._r26_ledger_finalizer_authorization is not None
    report = _path_a_report()
    authorization = _path_a_authorization()
    canonical_binding = ledger._binding_from_eligibility(report, authorization)
    assert canonical_binding is not None
    assert root._prepare_r26_protocol_marker_v1(canonical_binding).outcome == "prepared"
    prepared = composition.ledger_service.prepare(report, authorization, composition.ledger_store)
    assert prepared.prepared is True
    assert prepared.binding is not None
    binding = prepared.binding
    assert binding == canonical_binding
    snapshot = coordinator._page_store.load_revisioned(binding.project_id)
    context = coordinator._page_store.context_from_snapshot(snapshot, binding.page_id)
    next_context = context.advance(
        state=PageState.GENERATED,
        events=[WorkflowEvent(event_type=EventType.IMAGE_GENERATED, data={"state": "Generated"})],
        artifact_name=PageState.GENERATED.value,
        payload=external._descriptor(binding.output_asset_id),
    )
    project = coordinator._page_store.project_from_context(snapshot, binding.page_id, next_context)
    assert coordinator._record_r30_pre_cas_provenance(binding, snapshot) is True
    committed, intent_invalid = coordinator._authoritative_commit(binding, snapshot, context, project)
    assert committed is not None
    assert intent_invalid is False

    result = coordinator.apply(report, authorization)
    replay = coordinator.apply(report, authorization)

    assert result.status == "application_not_applied"
    assert result.code == "EXTERNAL_APPLICATION_R26_APPLIED"
    assert replay.code == "EXTERNAL_APPLICATION_APPLIED_REPLAY_CONFIRMED"
    assert root._observe_r26_protocol_marker_v2(binding).outcome == "APPLIED"
    with sqlite3.connect(composition.ledger_store._database_path) as connection:
        lifecycle = connection.execute(
            "SELECT lifecycle FROM workflow_application_ledger WHERE attempt_id = ?",
            (_PATH_A_ATTEMPT_ID,),
        ).fetchone()
    assert lifecycle == ("applied",)
    with sqlite3.connect(composition.receipt_store._database_path) as connection:
        receipt = connection.execute(
            "SELECT attempt_id FROM durable_application_commit_receipts WHERE attempt_id = ?",
            (_PATH_A_ATTEMPT_ID,),
        ).fetchone()
    assert receipt == (_PATH_A_ATTEMPT_ID,)
    r25 = coordinator._r25_localfile_composition
    assert r25 is not None
    with sqlite3.connect(r25._r25_store._database_path) as connection:
        count = connection.execute("SELECT COUNT(*) FROM post_cas_application_attestations").fetchone()
    assert count == (1,)

    # A new process owns no old proof, observation, or confirmation.  This
    # follows the existing private-host restart convention: only volatile
    # registries are cleared; the durable LocalFile state is unchanged.
    with private._REGISTRY_LOCK:
        private._ROOTS_BY_REPOSITORY.clear()
        private._REPOSITORY_BY_DURABLE_ROOT.clear()
    with ledger._R26_CAPABILITY_LOCK:
        ledger._R26_READY_ROOTS.clear()
        ledger._R26_PREPARATION_CAPABILITIES.clear()
        ledger._R26_OBSERVATION_CAPABILITIES.clear()
    restarted_root = private._create_private_real_delivery_workflow_host_v1(
        tmp_path / "private-host-path-a"
    )._start_private_real_delivery_composition_v1()
    restarted_coordinator = restarted_root._composition.external_application

    assert restarted_root._repository is not root._repository
    assert restarted_root._observe_r26_protocol_marker_v2(binding).outcome == "APPLIED"
    restarted_replay = restarted_coordinator.apply(report, authorization)

    assert restarted_replay.code == "EXTERNAL_APPLICATION_APPLIED_REPLAY_CONFIRMED"
    with sqlite3.connect(restarted_root._ledger_store._database_path) as connection:
        restarted_lifecycle = connection.execute(
            "SELECT lifecycle FROM workflow_application_ledger WHERE attempt_id = ?",
            (_PATH_A_ATTEMPT_ID,),
        ).fetchone()
    assert restarted_lifecycle == ("applied",)


def test_private_host_concurrent_canonical_invocations_serialize_and_replay(tmp_path: Path) -> None:
    """Start two real invocations together without requiring concurrent fence ownership."""

    root = _private_host_path_a_root(tmp_path)
    composition = root._composition
    coordinator = composition.external_application
    report = _path_a_report()
    authorization = _path_a_authorization()
    canonical_binding = ledger._binding_from_eligibility(report, authorization)
    assert canonical_binding is not None
    assert root._prepare_r26_protocol_marker_v1(canonical_binding).outcome == "prepared"
    prepared = composition.ledger_service.prepare(report, authorization, composition.ledger_store)
    assert prepared.prepared is True
    assert prepared.binding is not None
    binding = prepared.binding
    assert binding == canonical_binding
    snapshot = coordinator._page_store.load_revisioned(binding.project_id)
    context = coordinator._page_store.context_from_snapshot(snapshot, binding.page_id)
    next_context = context.advance(
        state=PageState.GENERATED,
        events=[WorkflowEvent(event_type=EventType.IMAGE_GENERATED, data={"state": "Generated"})],
        artifact_name=PageState.GENERATED.value,
        payload=external._descriptor(binding.output_asset_id),
    )
    project = coordinator._page_store.project_from_context(snapshot, binding.page_id, next_context)
    assert coordinator._record_r30_pre_cas_provenance(binding, snapshot) is True
    committed, intent_invalid = coordinator._authoritative_commit(binding, snapshot, context, project)
    assert committed is not None
    assert intent_invalid is False
    barrier = Barrier(2, timeout=5)

    def _apply() -> object:
        barrier.wait()
        return coordinator.apply(report, authorization)

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(_apply)
        future_b = executor.submit(_apply)
        try:
            result_a = future_a.result(timeout=10)
            result_b = future_b.result(timeout=10)
        finally:
            barrier.abort()

    assert sorted((result_a.code, result_b.code)) == [
        "EXTERNAL_APPLICATION_APPLIED_REPLAY_CONFIRMED",
        "EXTERNAL_APPLICATION_R26_APPLIED",
    ]
    assert root._observe_r26_protocol_marker_v2(binding).outcome == "APPLIED"
    with sqlite3.connect(composition.ledger_store._database_path) as connection:
        lifecycle_count = connection.execute(
            "SELECT COUNT(*) FROM workflow_application_ledger "
            "WHERE attempt_id = ? AND lifecycle = 'applied'",
            (_PATH_A_ATTEMPT_ID,),
        ).fetchone()
    assert lifecycle_count == (1,)


def test_exact_registered_finalizer_applies_one_marker_v1_row(tmp_path: Path) -> None:
    authorization, observation, root, binding = _ready_finalizer(tmp_path)

    result = ledger._finalize_r26_ledger_reconciliation_v1(authorization, observation)

    assert result.outcome == "APPLIED"
    assert root._observe_r26_protocol_marker_v2(binding).outcome == "APPLIED"


def test_store_has_no_unsealed_semantic_prepared_to_applied_inlet(tmp_path: Path) -> None:
    _authorization, observation, root, binding = _ready_finalizer(tmp_path, "no-bypass")

    unsealed_transition = getattr(
        root._ledger_store, "_finalize_r26_protocol_prepared_v1", None
    )

    assert unsealed_transition is None
    assert observation._used is False
    assert root._observe_r26_protocol_marker_v2(binding).outcome == "PREPARED"
    with sqlite3.connect(root._ledger_store._database_path) as connection:
        applied_count = connection.execute(
            "SELECT COUNT(*) FROM workflow_application_ledger WHERE lifecycle = 'applied'"
        ).fetchone()
    assert applied_count == (0,)


@pytest.mark.parametrize("value", [None, object()])
def test_finalizer_rejects_missing_or_forged_authorization(tmp_path: Path, value: object) -> None:
    _authorization, observation, root, binding = _ready_finalizer(tmp_path, "missing")

    result = ledger._finalize_r26_ledger_reconciliation_v1(value, observation)

    assert result.outcome == "CALL_REJECTED"
    assert root._observe_r26_protocol_marker_v2(binding).outcome == "PREPARED"


def test_finalizer_rejects_reconstructed_authorization_before_mutation(tmp_path: Path) -> None:
    _authorization, observation, root, binding = _ready_finalizer(tmp_path, "reconstructed")
    forged = object.__new__(ledger._R26LedgerFinalizerAuthorizationV1)
    object.__setattr__(forged, "_issuer", ledger._R26_FINALIZER_ISSUER)
    object.__setattr__(forged, "_used", False)

    result = ledger._finalize_r26_ledger_reconciliation_v1(forged, observation)

    assert result.outcome == "CALL_REJECTED"
    assert root._observe_r26_protocol_marker_v2(binding).outcome == "PREPARED"


def test_finalizer_authorization_copy_and_deepcopy_are_not_authority(tmp_path: Path) -> None:
    authorization, _observation, root, binding = _ready_finalizer(tmp_path, "auth-copies")

    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        copy.copy(authorization)
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        copy.deepcopy(authorization)
    assert root._observe_r26_protocol_marker_v2(binding).outcome == "PREPARED"


def test_finalizer_rejects_copied_and_reconstructed_observations(tmp_path: Path) -> None:
    authorization, observation, root, binding = _ready_finalizer(tmp_path, "observation")
    with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
        copy.copy(observation)
    forged = object.__new__(ledger._R26AuthenticatedProtocolObservationV1)
    result = ledger._finalize_r26_ledger_reconciliation_v1(authorization, forged)

    assert result.outcome == "CALL_REJECTED"
    assert root._observe_r26_protocol_marker_v2(binding).outcome == "PREPARED"


def test_prepared_observation_is_one_use_even_when_durable_call_reaches_the_ledger(tmp_path: Path) -> None:
    authorization, observation, _root, _binding_value = _ready_finalizer(tmp_path, "one-use")

    assert ledger._finalize_r26_ledger_reconciliation_v1(authorization, observation).outcome == "APPLIED"
    assert ledger._finalize_r26_ledger_reconciliation_v1(authorization, observation).outcome == "CALL_REJECTED"


def test_foreign_composition_authorization_is_rejected(tmp_path: Path) -> None:
    authorization, _observation, _root, _binding_value = _ready_finalizer(tmp_path, "first")
    _foreign_authorization, observation, root, binding = _ready_finalizer(tmp_path, "second")

    result = ledger._finalize_r26_ledger_reconciliation_v1(authorization, observation)

    assert result.outcome == "CALL_REJECTED"
    assert root._observe_r26_protocol_marker_v2(binding).outcome == "PREPARED"


@pytest.mark.parametrize("contenders", [2, 8, 32])
def test_same_authenticated_observation_has_one_finalizer_winner(
    tmp_path: Path, contenders: int
) -> None:
    authorization, observation, root, binding = _ready_finalizer(tmp_path, f"race-{contenders}")
    barrier = Barrier(contenders)

    def _finalize() -> str:
        barrier.wait()
        return ledger._finalize_r26_ledger_reconciliation_v1(
            authorization, observation
        ).outcome

    with ThreadPoolExecutor(max_workers=contenders) as executor:
        outcomes = [future.result() for future in [executor.submit(_finalize) for _ in range(contenders)]]

    assert outcomes.count("APPLIED") == 1
    assert outcomes.count("CALL_REJECTED") == contenders - 1
    assert root._observe_r26_protocol_marker_v2(binding).outcome == "APPLIED"


def test_finalizer_returns_conflict_for_tampered_prepared_marker(tmp_path: Path) -> None:
    authorization, observation, root, binding = _ready_finalizer(tmp_path, "conflict")
    with sqlite3.connect(root._ledger_store._database_path) as connection:
        connection.execute(
            "UPDATE workflow_application_ledger SET r26_protocol_binding_digest = ? "
            "WHERE attempt_id = ?",
            ("0" * 64, binding.attempt_id),
        )
        connection.commit()

    assert ledger._finalize_r26_ledger_reconciliation_v1(authorization, observation).outcome == "CORRUPT"


def test_finalizer_returns_corrupt_for_schema_drift_and_consumes_observation(
    tmp_path: Path,
) -> None:
    authorization, observation, root, _binding_value = _ready_finalizer(tmp_path, "corrupt")
    with sqlite3.connect(root._ledger_store._database_path) as connection:
        connection.execute("PRAGMA user_version = 99")
        connection.commit()

    assert ledger._finalize_r26_ledger_reconciliation_v1(authorization, observation).outcome == "CORRUPT"
    assert ledger._finalize_r26_ledger_reconciliation_v1(authorization, observation).outcome == "CALL_REJECTED"


def test_finalizer_transaction_unavailability_consumes_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    authorization, observation, _root, _binding_value = _ready_finalizer(tmp_path, "unavailable")

    def _unavailable(*_args: object, **_kwargs: object) -> sqlite3.Connection:
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(ledger, "_open_ledger_connection", _unavailable)
    assert ledger._finalize_r26_ledger_reconciliation_v1(authorization, observation).outcome == "RECOVERY_REQUIRED"
    assert ledger._finalize_r26_ledger_reconciliation_v1(authorization, observation).outcome == "CALL_REJECTED"


def test_stale_prepared_observation_cannot_apply_after_another_exact_observation(
    tmp_path: Path,
) -> None:
    authorization, stale_observation, root, binding = _ready_finalizer(tmp_path, "stale")
    fresh_observation = root._observe_r26_protocol_marker_v2(binding)

    assert ledger._finalize_r26_ledger_reconciliation_v1(authorization, fresh_observation).outcome == "APPLIED"
    assert ledger._finalize_r26_ledger_reconciliation_v1(authorization, stale_observation).outcome == "CONFLICT"
    assert root._observe_r26_protocol_marker_v2(binding).outcome == "APPLIED"


def test_distinct_prepared_observations_have_one_durable_winner(tmp_path: Path) -> None:
    authorization, first, root, binding = _ready_finalizer(tmp_path, "distinct-race")
    second = root._observe_r26_protocol_marker_v2(binding)
    barrier = Barrier(2)

    def _finalize(observation: object) -> str:
        barrier.wait()
        return ledger._finalize_r26_ledger_reconciliation_v1(authorization, observation).outcome

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = [
            future.result()
            for future in [
                executor.submit(_finalize, first),
                executor.submit(_finalize, second),
            ]
        ]

    assert sorted(outcomes) == ["APPLIED", "CONFLICT"]
    assert root._observe_r26_protocol_marker_v2(binding).outcome == "APPLIED"


def test_confirmation_path_a_tombstones_after_applied_finalization(tmp_path: Path) -> None:
    coordinator, confirmation, binding, invocation, fence, context, root = _live_confirmation(
        tmp_path, "path-a"
    )
    try:
        assert root._prepare_r26_protocol_marker_v1(binding).outcome == "prepared"
        outcome = coordinator._finalize_r26_ledger_from_confirmation_v1(
            confirmation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._r25_localfile_composition,
            invocation,
            root._observe_r26_protocol_marker_v2(binding),
        )

        assert outcome == "APPLIED"
        assert root._observe_r26_protocol_marker_v2(binding).outcome == "APPLIED"
        assert coordinator._begin_r26_receipt_confirmation_consumption_v1(
            confirmation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._r25_localfile_composition,
            invocation,
        ) == "CONSUMED"
    finally:
        _release_confirmation_context(coordinator, context, fence)


def test_confirmation_path_b_applied_marker_consumes_without_second_finalizer_call(
    tmp_path: Path,
) -> None:
    coordinator, confirmation, binding, invocation, fence, context, root = _live_confirmation(
        tmp_path, "path-b"
    )
    try:
        assert root._prepare_r26_protocol_marker_v1(binding).outcome == "prepared"
        authorization = coordinator._r26_ledger_finalizer_authorization
        assert ledger._finalize_r26_ledger_reconciliation_v1(
            authorization, root._observe_r26_protocol_marker_v2(binding)
        ).outcome == "APPLIED"

        assert coordinator._begin_r26_receipt_confirmation_consumption_v1(
            confirmation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._r25_localfile_composition,
            invocation,
        ) == "CONSUMING"
        coordinator._tombstone_r26_receipt_confirmation_v1(confirmation)
        assert root._observe_r26_protocol_marker_v2(binding).outcome == "APPLIED"
        assert coordinator._begin_r26_receipt_confirmation_consumption_v1(
            confirmation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._r25_localfile_composition,
            invocation,
        ) == "CONSUMED"
    finally:
        _release_confirmation_context(coordinator, context, fence)


def test_confirmation_tombstones_after_rejected_observation(tmp_path: Path) -> None:
    coordinator, confirmation, binding, invocation, fence, context, _root = _live_confirmation(
        tmp_path, "rejected-confirmation"
    )
    try:
        assert coordinator._finalize_r26_ledger_from_confirmation_v1(
            confirmation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._r25_localfile_composition,
            invocation,
            object(),
        ) == "AUTHORITY_REJECTED"
        assert coordinator._begin_r26_receipt_confirmation_consumption_v1(
            confirmation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._r25_localfile_composition,
            invocation,
        ) == "CONSUMED"
    finally:
        _release_confirmation_context(coordinator, context, fence)


def test_confirmation_rejects_nonexact_authority_inputs_without_consuming_exact_confirmation(
    tmp_path: Path,
) -> None:
    coordinator, confirmation, binding, invocation, fence, context, _root = _live_confirmation(
        tmp_path, "exact"
    )
    foreign_coordinator, foreign_confirmation, _foreign_binding, foreign_invocation, foreign_fence, foreign_context, _foreign_root = _live_confirmation(
        tmp_path, "foreign"
    )
    reconstructed = object.__new__(external._ExactReceiptReconciliationConfirmationV1)
    object.__setattr__(reconstructed, "_seal", confirmation._seal)
    try:
        with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
            copy.copy(confirmation)
        with pytest.raises(ValueError, match="AUTHORITY_REJECTED"):
            copy.deepcopy(confirmation)
        mismatches = (
            (
                "reconstructed confirmation",
                reconstructed,
                coordinator._r26_proof_factory,
                binding,
                coordinator._r25_localfile_composition,
                invocation,
            ),
            (
                "foreign factory",
                confirmation,
                foreign_coordinator._r26_proof_factory,
                binding,
                coordinator._r25_localfile_composition,
                invocation,
            ),
            (
                "equal-value binding",
                confirmation,
                coordinator._r26_proof_factory,
                binding.model_copy(),
                coordinator._r25_localfile_composition,
                invocation,
            ),
            (
                "replacement composition",
                confirmation,
                coordinator._r26_proof_factory,
                binding,
                object(),
                invocation,
            ),
            (
                "foreign invocation",
                confirmation,
                coordinator._r26_proof_factory,
                binding,
                coordinator._r25_localfile_composition,
                foreign_invocation,
            ),
        )
        for label, *candidate in mismatches:
            assert (
                coordinator._begin_r26_receipt_confirmation_consumption_v1(*candidate)
                == "AUTHORITY_REJECTED"
            ), label
        assert foreign_coordinator._begin_r26_receipt_confirmation_consumption_v1(
            confirmation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._r25_localfile_composition,
            invocation,
        ) == "AUTHORITY_REJECTED"
        assert coordinator._begin_r26_receipt_confirmation_consumption_v1(
            confirmation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._r25_localfile_composition,
            invocation,
        ) == "CONSUMING"
        coordinator._tombstone_r26_receipt_confirmation_v1(confirmation)
    finally:
        foreign_coordinator._tombstone_r26_receipt_confirmation_v1(foreign_confirmation)
        _release_confirmation_context(coordinator, context, fence)
        _release_confirmation_context(foreign_coordinator, foreign_context, foreign_fence)


def test_fence_invocation_rejects_replacement_page_store_without_consuming(
    tmp_path: Path,
) -> None:
    root = private._create_private_real_delivery_workflow_host_v1(
        tmp_path / "page-store"
    )._start_private_real_delivery_composition_v1()
    coordinator = root._composition.external_application
    binding = _binding("page-store")
    fence = WindowsPageExecutionFence(binding.project_id, binding.page_id)
    fence.acquire()
    context = external._ExternalApplicationFenceContext._create(
        binding, SimpleNamespace(revision=7, fingerprint="a" * 64)
    )
    coordinator._r26_active_fence_contexts.add(context)
    try:
        invocation = coordinator._issue_r26_fence_invocation_authority_v1(
            binding, fence, context
        )
        assert not coordinator._consume_r26_fence_invocation_authority_v1(
            invocation,
            coordinator._r26_proof_factory,
            binding,
            object(),
        )
        assert coordinator._consume_r26_fence_invocation_authority_v1(
            invocation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._page_store,
        )
    finally:
        _release_confirmation_context(coordinator, context, fence)


def test_confirmation_tombstones_after_corrupt_durable_marker(tmp_path: Path) -> None:
    coordinator, confirmation, binding, invocation, fence, context, root = _live_confirmation(
        tmp_path, "corrupt-confirmation"
    )
    try:
        assert root._prepare_r26_protocol_marker_v1(binding).outcome == "prepared"
        observation = root._observe_r26_protocol_marker_v2(binding)
        with sqlite3.connect(root._ledger_store._database_path) as connection:
            connection.execute("PRAGMA user_version = 99")
            connection.commit()
        assert coordinator._finalize_r26_ledger_from_confirmation_v1(
            confirmation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._r25_localfile_composition,
            invocation,
            observation,
        ) == "CORRUPT"
        assert coordinator._begin_r26_receipt_confirmation_consumption_v1(
            confirmation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._r25_localfile_composition,
            invocation,
        ) == "CONSUMED"
    finally:
        _release_confirmation_context(coordinator, context, fence)


def test_confirmation_tombstones_after_transaction_unavailability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    coordinator, confirmation, binding, invocation, fence, context, root = _live_confirmation(
        tmp_path, "unavailable-confirmation"
    )

    def _unavailable(*_args: object, **_kwargs: object) -> sqlite3.Connection:
        raise sqlite3.OperationalError("database is locked")

    try:
        assert root._prepare_r26_protocol_marker_v1(binding).outcome == "prepared"
        observation = root._observe_r26_protocol_marker_v2(binding)
        monkeypatch.setattr(ledger, "_open_ledger_connection", _unavailable)
        assert coordinator._finalize_r26_ledger_from_confirmation_v1(
            confirmation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._r25_localfile_composition,
            invocation,
            observation,
        ) == "RECOVERY_REQUIRED"
        assert coordinator._begin_r26_receipt_confirmation_consumption_v1(
            confirmation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._r25_localfile_composition,
            invocation,
        ) == "CONSUMED"
        assert root._observe_r26_protocol_marker_v2(binding).outcome == "PREPARED"
    finally:
        _release_confirmation_context(coordinator, context, fence)


def test_confirmation_tombstones_after_corrupt_prepared_marker(tmp_path: Path) -> None:
    coordinator, confirmation, binding, invocation, fence, context, root = _live_confirmation(
        tmp_path, "conflict"
    )
    try:
        assert root._prepare_r26_protocol_marker_v1(binding).outcome == "prepared"
        observation = root._observe_r26_protocol_marker_v2(binding)
        with sqlite3.connect(root._ledger_store._database_path) as connection:
            connection.execute(
                "UPDATE workflow_application_ledger SET r26_protocol_binding_digest = ? "
                "WHERE attempt_id = ?",
                ("0" * 64, binding.attempt_id),
            )
            connection.commit()
        assert coordinator._finalize_r26_ledger_from_confirmation_v1(
            confirmation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._r25_localfile_composition,
            invocation,
            observation,
        ) == "CORRUPT"
        assert coordinator._begin_r26_receipt_confirmation_consumption_v1(
            confirmation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._r25_localfile_composition,
            invocation,
        ) == "CONSUMED"
    finally:
        _release_confirmation_context(coordinator, context, fence)


def test_confirmation_tombstones_after_stale_observation_loses_to_applied_winner(tmp_path: Path) -> None:
    coordinator, confirmation, binding, invocation, fence, context, root = _live_confirmation(
        tmp_path, "stale"
    )
    try:
        assert root._prepare_r26_protocol_marker_v1(binding).outcome == "prepared"
        stale_observation = root._observe_r26_protocol_marker_v2(binding)
        winning_observation = root._observe_r26_protocol_marker_v2(binding)
        assert ledger._finalize_r26_ledger_reconciliation_v1(
            coordinator._r26_ledger_finalizer_authorization, winning_observation
        ).outcome == "APPLIED"
        assert coordinator._finalize_r26_ledger_from_confirmation_v1(
            confirmation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._r25_localfile_composition,
            invocation,
            stale_observation,
        ) == "CONFLICT"
        assert root._observe_r26_protocol_marker_v2(binding).outcome == "APPLIED"
        assert coordinator._begin_r26_receipt_confirmation_consumption_v1(
            confirmation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._r25_localfile_composition,
            invocation,
        ) == "CONSUMED"
    finally:
        _release_confirmation_context(coordinator, context, fence)


def test_acknowledgement_loss_tombstones_confirmation_and_requires_fresh_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    coordinator, confirmation, binding, invocation, fence, context, root = _live_confirmation(
        tmp_path, "ack"
    )
    real_open = ledger._open_ledger_connection

    class _AcknowledgementLossConnection:
        def __init__(self, connection: sqlite3.Connection) -> None:
            self._connection = connection

        def __getattr__(self, name: str) -> object:
            return getattr(self._connection, name)

        def commit(self) -> None:
            self._connection.commit()
            raise sqlite3.OperationalError("acknowledgement lost")

    def _acknowledgement_loss(database_path: Path) -> object:
        return _AcknowledgementLossConnection(real_open(database_path))

    try:
        assert root._prepare_r26_protocol_marker_v1(binding).outcome == "prepared"
        observation = root._observe_r26_protocol_marker_v2(binding)
        monkeypatch.setattr(ledger, "_open_ledger_connection", _acknowledgement_loss)
        assert coordinator._finalize_r26_ledger_from_confirmation_v1(
            confirmation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._r25_localfile_composition,
            invocation,
            observation,
        ) == "LEDGER_REPLAY_REQUIRED"
        assert root._observe_r26_protocol_marker_v2(binding).outcome == "APPLIED"
        assert coordinator._begin_r26_receipt_confirmation_consumption_v1(
            confirmation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._r25_localfile_composition,
            invocation,
        ) == "CONSUMED"
    finally:
        _release_confirmation_context(coordinator, context, fence)


@pytest.mark.parametrize("after_durable_result", [False, True])
def test_finalizer_wrapper_failure_tombstones_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, after_durable_result: bool
) -> None:
    coordinator, confirmation, binding, invocation, fence, context, root = _live_confirmation(
        tmp_path, f"wrap-{after_durable_result}"
    )
    real_finalizer = external._finalize_r26_ledger_reconciliation_v1

    def _failing_finalizer(authorization: object, observation: object) -> object:
        if after_durable_result:
            assert real_finalizer(authorization, observation).outcome == "APPLIED"
        raise RuntimeError("controlled finalizer seam failure")

    try:
        assert root._prepare_r26_protocol_marker_v1(binding).outcome == "prepared"
        monkeypatch.setattr(external, "_finalize_r26_ledger_reconciliation_v1", _failing_finalizer)
        coordinator._r26_ledger_finalizer = _failing_finalizer
        assert coordinator._finalize_r26_ledger_from_confirmation_v1(
            confirmation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._r25_localfile_composition,
            invocation,
            root._observe_r26_protocol_marker_v2(binding),
        ) == "RECONCILIATION_RESTART_REQUIRED"
        expected = "APPLIED" if after_durable_result else "PREPARED"
        assert root._observe_r26_protocol_marker_v2(binding).outcome == expected
        assert coordinator._begin_r26_receipt_confirmation_consumption_v1(
            confirmation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._r25_localfile_composition,
            invocation,
        ) == "CONSUMED"
    finally:
        _release_confirmation_context(coordinator, context, fence)


@pytest.mark.parametrize("contenders", [2, 8, 32])
def test_same_confirmation_has_one_consuming_winner_and_terminal_losers(
    tmp_path: Path, contenders: int
) -> None:
    coordinator, confirmation, binding, invocation, fence, context, _root = _live_confirmation(
        tmp_path, f"confirmation-race-{contenders}"
    )
    barrier = Barrier(contenders)

    def _consume() -> str:
        barrier.wait()
        return coordinator._begin_r26_receipt_confirmation_consumption_v1(
            confirmation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._r25_localfile_composition,
            invocation,
        )

    try:
        with ThreadPoolExecutor(max_workers=contenders) as executor:
            outcomes = [
                future.result()
                for future in [executor.submit(_consume) for _ in range(contenders)]
            ]
        assert outcomes.count("CONSUMING") == 1
        assert outcomes.count("CONSUMED") == contenders - 1
        coordinator._tombstone_r26_receipt_confirmation_v1(confirmation)
        assert coordinator._begin_r26_receipt_confirmation_consumption_v1(
            confirmation,
            coordinator._r26_proof_factory,
            binding,
            coordinator._r25_localfile_composition,
            invocation,
        ) == "CONSUMED"
    finally:
        _release_confirmation_context(coordinator, context, fence)
