"""Private R30/R31 trusted pairing foundation for future R25 materialization.

This module creates no R25 row and performs no Coordinator, CAS, provider,
Receipt, Ledger, or StateMachine action.  It only assembles the exact
same-process LocalFile objects that a later canonical Coordinator inlet may
use.  Object identity is a composition boundary, not a hostile-code sandbox.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Final, Literal, cast

from manga_director.production.future_real_delivery_binding_authority import (
    RealDeliveryBindingAuthorityV1,
    _BindingReplayFailureV1,
    _HistoricalBindingFactsV1,
)
from manga_director.production.future_real_delivery_r18_construction import (
    PrivateR18CompositionFactoryV1,
)
from manga_director.production.future_real_delivery_r25_attestation import (
    _canonical_json,
    _canonical_r25_record_v1,
    _construct_r25_attestation_store_v1,
    _construct_r25_materialization_service_v1,
    _digest,
    _R25AttestationStoreV1,
    _R25MaterializationServiceV1,
)
from manga_director.production.future_real_delivery_r30_pre_cas_ledger_provenance import (
    _canonical_r30_pre_cas_provenance_v1,
    _construct_r30_pre_cas_ledger_provenance_store_v1,
    _R30PreCasLedgerProvenanceStoreV1,
    _R30PreCasProvenanceRecordV1,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    WorkflowApplicationLedgerBindingDTO,
    WorkflowApplicationLedgerReport,
    _WorkflowApplicationLedgerObservationV1,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.local_file_aggregate_envelope import (
    _decode_r27_aggregate,
    _physical_fingerprint,
)
from manga_director.repositories.local_file_durability import (
    LocalFileDurabilityError,
    _r27_lineage_identity,
    _R27CommittedRecord,
    _validate_r27_aggregate,
)

_PAIRING_REGISTRY: Final[dict[object, tuple[object, ...]]] = {}
_RESTART_INGRESS_REGISTRY: Final[dict[object, tuple[object, ...]]] = {}


class _R20ReplayFailureV1(ValueError):
    """Private structured result from the read-only R20 companion boundary."""

    __slots__ = ("outcome",)

    outcome: Literal["AUTHORITY_REJECTED", "CORRUPT", "NOT_FOUND", "RECOVERY_REQUIRED"]

    def __init__(
        self, outcome: Literal["AUTHORITY_REJECTED", "CORRUPT", "NOT_FOUND", "RECOVERY_REQUIRED"]
    ) -> None:
        super().__init__(outcome)
        self.outcome = outcome


def _rejected() -> ValueError:
    return ValueError("AUTHORITY_REJECTED")


def _corrupt() -> ValueError:
    return ValueError("CORRUPT")


def _recovery_required() -> ValueError:
    return ValueError("RECOVERY_REQUIRED")


@dataclass(frozen=True, slots=True)
class _CommittedR27LineageFactsV1:
    """Facts read only from one validated, durable R27 committed lineage."""

    authoritative_envelope_fingerprint: str
    lineage_identity: str
    lineage_json: str
    physical_aggregate_fingerprint: str
    project_id: str
    revision: int


class _R20CompanionReaderV1:
    """Private additive wrapper over the existing R20 historical replay."""

    __slots__ = ("_authority", "_repository")

    _authority: RealDeliveryBindingAuthorityV1
    _repository: LocalFileRepository

    def __init__(self, *args: object) -> None:
        del args
        raise _rejected()

    def _replay_exact_v1(self, delivery_identity: object) -> _HistoricalBindingFactsV1:
        """Delegate to the unchanged read-only R20 replay boundary."""

        if type(delivery_identity) is not str:
            raise _rejected()
        return self._authority._replay_historical_binding_exact_v1(delivery_identity)

    def _replay_for_binding_v1(
        self, binding: object
    ) -> _HistoricalBindingFactsV1:
        """Read one existing R20 record selected by the Coordinator's binding."""

        if type(binding) is not WorkflowApplicationLedgerBindingDTO:
            raise _rejected()
        try:
            facts = self._authority._replay_historical_binding_for_attempt_v1(binding.attempt_id)
        except _BindingReplayFailureV1 as error:
            raise _R20ReplayFailureV1(error.outcome) from error
        except ValueError as error:
            raise _R20ReplayFailureV1("CORRUPT") from error
        if (
            facts.attempt_id != binding.attempt_id
            or facts.project_id != binding.project_id
            or facts.page_id != binding.page_id
            or facts.target_page_reference != binding.target_page_reference
            or facts.provider_reference != binding.provider_reference
            or facts.logical_output_id != binding.output_asset_id
        ):
            raise _R20ReplayFailureV1("CORRUPT")
        return facts


class _CommittedR27LineageReaderV1:
    """Read only an already durable R29/R27 committed lineage for one project."""

    __slots__ = ("_repository",)

    _repository: LocalFileRepository

    def __init__(self, *args: object) -> None:
        del args
        raise _rejected()

    def _read_exact_committed_v1(self, project_id: object) -> _CommittedR27LineageFactsV1:
        """Validate committed metadata, activation, frame, F0, F1, and lineage.

        ``project_id`` is only a private read selector.  A later sealed
        Coordinator request must bind this result to R18/R20 and current-page
        facts before it can reach the R25 service.
        """

        if type(project_id) is not str or not project_id:
            raise _rejected()
        try:
            repository = self._repository
            snapshot = repository._revision_store._capture_r29_pre_reconciliation_snapshot(
                project_id, repository._path(project_id)
            )
        except LocalFileDurabilityError as error:
            raise _recovery_required() from error
        activation = snapshot.activation
        committed = snapshot.committed
        if (
            snapshot.aggregate_state != "R27"
            or snapshot.metadata_state != "V2_COMMITTED"
            or activation is None
            or activation.state != "R27_COMMITTED"
            or activation.project_id != project_id
            or not isinstance(committed, _R27CommittedRecord)
        ):
            raise _recovery_required()
        try:
            envelope = _decode_r27_aggregate(snapshot.aggregate_payload)
            if envelope is None:
                raise _corrupt()
            if _physical_fingerprint(snapshot.aggregate_payload) != committed.record.fingerprint:
                raise _corrupt()
            _validate_r27_aggregate(snapshot.aggregate_payload, committed.record, committed.lineage)
            lineage_identity = _r27_lineage_identity(committed.lineage)
            lineage_json = json.dumps(
                committed.lineage, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            )
        except (LocalFileDurabilityError, TypeError, ValueError) as error:
            raise _corrupt() from error
        if (
            committed.record.project_id != project_id
            or activation.committed_aggregate_fingerprint != committed.record.fingerprint
            or activation.committed_revision != committed.record.revision
            or activation.source_lineage_identity != lineage_identity
        ):
            raise _corrupt()
        return _CommittedR27LineageFactsV1(
            authoritative_envelope_fingerprint=envelope.authoritative_envelope_fingerprint,
            lineage_identity=lineage_identity,
            lineage_json=lineage_json,
            physical_aggregate_fingerprint=committed.record.fingerprint,
            project_id=project_id,
            revision=committed.record.revision,
        )

    def _read_for_binding_v1(
        self,
        binding: object,
        *,
        post_commit_fingerprint: object,
        post_commit_revision: object,
    ) -> _CommittedR27LineageFactsV1:
        """Read a committed lineage and bind it to exact post-CAS facts."""

        if (
            type(binding) is not WorkflowApplicationLedgerBindingDTO
            or type(post_commit_revision) is not int
            or post_commit_revision < 1
            or not _sha256(post_commit_fingerprint)
        ):
            raise _rejected()
        facts = self._read_exact_committed_v1(binding.project_id)
        try:
            lineage = json.loads(facts.lineage_json)
        except (TypeError, ValueError) as error:
            raise _corrupt() from error
        if type(lineage) is not dict:
            raise _corrupt()
        if (
            facts.revision != post_commit_revision
            or facts.physical_aggregate_fingerprint != post_commit_fingerprint
            or lineage.get("application_binding_identity") != _r27_application_binding_identity(binding)
            or lineage.get("attempt_id") != binding.attempt_id
            or lineage.get("project_id") != binding.project_id
            or lineage.get("page_id") != binding.page_id
            or lineage.get("target_page_reference") != binding.target_page_reference
            or lineage.get("source_state") != binding.source_state
            or lineage.get("target_state") != binding.target_state
            or lineage.get("resulting_revision") != post_commit_revision
        ):
            raise _corrupt()
        return facts


class _R25LocalFileCompositionV1:
    """One registry-bound private tuple for a canonical LocalFile composition."""

    __slots__ = ("_nonce", "_r18_authority", "_r20_reader", "_r25_service", "_r25_store", "_r27_reader", "_r30_provenance_store", "_repository")

    _nonce: object
    _r18_authority: RealDeliveryBindingAuthorityV1
    _r20_reader: _R20CompanionReaderV1
    _r25_service: _R25MaterializationServiceV1
    _r25_store: _R25AttestationStoreV1
    _r27_reader: _CommittedR27LineageReaderV1
    _r30_provenance_store: _R30PreCasLedgerProvenanceStoreV1
    _repository: LocalFileRepository

    def __init__(self, *args: object) -> None:
        del args
        raise _rejected()


class _R30PreCASPreparedRestartIngressV1:
    """One-use private R30 restart handoff, bound to observed authoritative facts."""

    __slots__ = ()

    def __init__(self, *args: object) -> None:
        del args
        raise _rejected()


def _construct_localfile_r25_composition_v1(repository: object) -> _R25LocalFileCompositionV1:
    """Create the R31 Model A tuple from exactly the caller's LocalFile driver."""

    if type(repository) is not LocalFileRepository:
        raise _rejected()
    factory = PrivateR18CompositionFactoryV1()
    r18_composition = factory._create_for_existing_repository_v1(repository)
    r18_authority = factory.construct_authority(r18_composition)
    if r18_authority._repository is not repository:
        raise _rejected()
    r20_reader = object.__new__(_R20CompanionReaderV1)
    object.__setattr__(r20_reader, "_authority", r18_authority)
    object.__setattr__(r20_reader, "_repository", repository)
    r27_reader = object.__new__(_CommittedR27LineageReaderV1)
    object.__setattr__(r27_reader, "_repository", repository)
    r25_store = _construct_r25_attestation_store_v1(repository)
    r25_service = _construct_r25_materialization_service_v1(r25_store)
    r30_provenance_store = _construct_r30_pre_cas_ledger_provenance_store_v1(repository)
    composition = object.__new__(_R25LocalFileCompositionV1)
    nonce = object()
    object.__setattr__(composition, "_nonce", nonce)
    object.__setattr__(composition, "_repository", repository)
    object.__setattr__(composition, "_r18_authority", r18_authority)
    object.__setattr__(composition, "_r20_reader", r20_reader)
    object.__setattr__(composition, "_r27_reader", r27_reader)
    object.__setattr__(composition, "_r25_store", r25_store)
    object.__setattr__(composition, "_r25_service", r25_service)
    object.__setattr__(composition, "_r30_provenance_store", r30_provenance_store)
    _PAIRING_REGISTRY[nonce] = (
        repository,
        r18_authority,
        r20_reader,
        r27_reader,
        r25_store,
        r25_service,
        r30_provenance_store,
    )
    return composition


def _require_exact_localfile_r25_composition_v1(
    composition: object, repository: object
) -> _R25LocalFileCompositionV1:
    """Reject copied, mixed, foreign, and reconstructed private tuple objects."""

    if type(composition) is not _R25LocalFileCompositionV1 or type(repository) is not LocalFileRepository:
        raise _rejected()
    exact = composition
    issued = _PAIRING_REGISTRY.get(exact._nonce)
    if issued is None or not all(
        actual is expected
        for actual, expected in zip(
            issued,
            (
                repository,
                exact._r18_authority,
                exact._r20_reader,
                exact._r27_reader,
                exact._r25_store,
                exact._r25_service,
                exact._r30_provenance_store,
            ),
            strict=True,
        )
    ):
        raise _rejected()
    if not (
        exact._repository is repository
        and exact._r18_authority._repository is repository
        and exact._r20_reader._repository is repository
        and exact._r27_reader._repository is repository
        and exact._r25_service._store is exact._r25_store
    ):
        raise _rejected()
    return exact


def _record_normal_r30_pre_cas_provenance_v1(
    composition: object,
    repository: object,
    binding: object,
    *,
    expected_pre_cas_revision: object,
    expected_pre_cas_fingerprint: object,
) -> bool:
    """Persist only the normal in-fence prepared predecessor before R27 CAS."""

    if type(binding) is not WorkflowApplicationLedgerBindingDTO:
        raise _rejected()
    exact = _require_exact_localfile_r25_composition_v1(composition, repository)
    record = _canonical_r30_pre_cas_provenance_v1(
        binding,
        expected_pre_cas_revision=expected_pre_cas_revision,
        expected_pre_cas_fingerprint=expected_pre_cas_fingerprint,
    )
    outcome, returned = exact._r30_provenance_store._create_or_confirm_v1(record)
    return outcome in {"CREATED", "EXACT_REPLAY"} and returned == record


def _issue_r30_restart_ingress_v1(
    composition: object,
    repository: object,
    binding: object,
    ledger_observation: object,
) -> _R30PreCASPreparedRestartIngressV1:
    """Issue only after readonly observations prove the narrow R30 restart predicate."""

    if (
        type(binding) is not WorkflowApplicationLedgerBindingDTO
        or type(ledger_observation) is not _WorkflowApplicationLedgerObservationV1
        or ledger_observation.outcome != "PREPARED"
    ):
        raise _rejected()
    exact = _require_exact_localfile_r25_composition_v1(composition, repository)
    provenance = exact._r30_provenance_store._read_exact_v1(binding)
    if provenance is None:
        raise _recovery_required()
    r27 = _restart_r27_lineage_for_provenance(exact, binding, provenance)
    r20 = exact._r20_reader._replay_for_binding_v1(binding)
    ingress = object.__new__(_R30PreCASPreparedRestartIngressV1)
    _RESTART_INGRESS_REGISTRY[ingress] = (exact, binding, provenance, r27, r20)
    return ingress


def _consume_r30_restart_ingress_and_materialize_v1(
    composition: object,
    repository: object,
    ingress: object,
    prepare_report: object,
) -> bool:
    """Consume a sealed ingress after exact prepare confirmation and reread facts."""

    exact = _require_exact_localfile_r25_composition_v1(composition, repository)
    if type(ingress) is not _R30PreCASPreparedRestartIngressV1:
        raise _rejected()
    facts = _RESTART_INGRESS_REGISTRY.pop(ingress, None)
    if facts is None or facts[0] is not exact:
        raise _rejected()
    _composition, stored_binding, stored_provenance, stored_r27, stored_r20 = facts
    if (
        type(stored_binding) is not WorkflowApplicationLedgerBindingDTO
        or type(stored_provenance) is not _R30PreCasProvenanceRecordV1
        or type(stored_r27) is not _CommittedR27LineageFactsV1
        or type(stored_r20) is not _HistoricalBindingFactsV1
    ):
        return False
    binding = stored_binding
    provenance = stored_provenance
    r27 = stored_r27
    r20 = stored_r20
    if (
        type(prepare_report) is not WorkflowApplicationLedgerReport
        or prepare_report.binding != binding
        or prepare_report.prepared is not True
        or prepare_report.applied is not False
        or prepare_report.idempotent_replay is not True
    ):
        return False
    if exact._r30_provenance_store._read_exact_v1(binding) != provenance:
        return False
    if _restart_r27_lineage_for_provenance(exact, binding, provenance) != r27:
        return False
    if exact._r20_reader._replay_for_binding_v1(binding) != r20:
        return False
    return _materialize_r25_from_facts(binding, r27, r20, provenance.values[11], provenance.values[12], exact)


def _restart_r27_lineage_for_provenance(
    composition: _R25LocalFileCompositionV1,
    binding: WorkflowApplicationLedgerBindingDTO,
    provenance: _R30PreCasProvenanceRecordV1,
) -> _CommittedR27LineageFactsV1:
    r27 = composition._r27_reader._read_exact_committed_v1(binding.project_id)
    try:
        lineage = json.loads(r27.lineage_json)
    except (TypeError, ValueError) as error:
        raise _corrupt() from error
    if type(lineage) is not dict:
        raise _corrupt()
    if (
        lineage.get("application_binding_identity") != _r27_application_binding_identity(binding)
        or lineage.get("attempt_id") != binding.attempt_id
        or lineage.get("project_id") != binding.project_id
        or lineage.get("page_id") != binding.page_id
        or lineage.get("target_page_reference") != binding.target_page_reference
        or lineage.get("source_state") != binding.source_state
        or lineage.get("target_state") != binding.target_state
        or lineage.get("expected_revision") != provenance.values[11]
        or lineage.get("expected_aggregate_fingerprint") != provenance.values[12]
        or lineage.get("resulting_revision") != r27.revision
    ):
        raise _corrupt()
    return r27


def _materialize_normal_r25_v1(
    composition: object,
    repository: object,
    binding: object,
    *,
    post_commit_fingerprint: object,
    post_commit_revision: object,
) -> bool:
    """Perform the sole private normal R25 create-or-confirm operation.

    The caller must already hold the canonical page fence and have completed
    the existing post-CAS correlation.  All predecessor reads happen before
    the R25 service receives its one-use request.
    """

    if type(binding) is not WorkflowApplicationLedgerBindingDTO:
        raise _rejected()
    exact = _require_exact_localfile_r25_composition_v1(composition, repository)
    r27 = exact._r27_reader._read_for_binding_v1(
        binding,
        post_commit_fingerprint=post_commit_fingerprint,
        post_commit_revision=post_commit_revision,
    )
    r20 = exact._r20_reader._replay_for_binding_v1(binding)
    try:
        lineage = json.loads(r27.lineage_json)
    except (TypeError, ValueError) as error:
        raise _corrupt() from error
    if type(lineage) is not dict:
        raise _corrupt()
    expected_revision = lineage.get("expected_revision")
    expected_fingerprint = lineage.get("expected_aggregate_fingerprint")
    if type(expected_revision) is not int or expected_revision < 1 or not _sha256(expected_fingerprint):
        raise _corrupt()
    return _materialize_r25_from_facts(
        binding, r27, r20, expected_revision, cast(str, expected_fingerprint), exact
    )


def _materialize_r25_from_facts(
    binding: WorkflowApplicationLedgerBindingDTO,
    r27: _CommittedR27LineageFactsV1,
    r20: _HistoricalBindingFactsV1,
    pre_commit_revision: str | int,
    pre_commit_fingerprint: str | int,
    composition: _R25LocalFileCompositionV1,
) -> bool:
    """Create-or-confirm a row from facts already authenticated by a private inlet."""

    if (
        type(pre_commit_revision) is not int
        or pre_commit_revision < 1
        or not _sha256(pre_commit_fingerprint)
    ):
        raise _corrupt()
    application_binding_json = _r27_application_binding_json(binding)
    record = _canonical_r25_record_v1(
        delivery_identity=r20.delivery_identity,
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
        pre_commit_revision=pre_commit_revision,
        pre_commit_fingerprint=cast(str, pre_commit_fingerprint),
        post_commit_revision=r27.revision,
        post_commit_fingerprint=r27.physical_aggregate_fingerprint,
        application_binding_json=application_binding_json,
    )
    request = composition._r25_service._issue_for_trusted_record_v1(record)
    result, returned = composition._r25_service._materialize_v1(request)
    if result not in {"ATTESTED", "ATTESTED_REPLAY"} or returned != record:
        return False
    return True


def _r27_application_binding_json(binding: WorkflowApplicationLedgerBindingDTO) -> str:
    return _canonical_json(
        {
            "attempt_id": binding.attempt_id,
            "authorization_id": binding.authorization_id,
            "output_asset_id": binding.output_asset_id,
            "page_id": binding.page_id,
            "project_id": binding.project_id,
            "provider_reference": binding.provider_reference,
            "schema": "manga_director.r27.application-binding",
            "source_state": binding.source_state,
            "target_page_reference": binding.target_page_reference,
            "target_state": binding.target_state,
            "version": 1,
        }
    )


def _r27_application_binding_identity(binding: WorkflowApplicationLedgerBindingDTO) -> str:
    return _digest(_r27_application_binding_json(binding))


def _sha256(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )
