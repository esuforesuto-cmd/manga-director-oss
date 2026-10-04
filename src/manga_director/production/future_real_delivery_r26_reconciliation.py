"""Private, volatile R26 reconciliation-proof authority.

This module deliberately has no workflow import and owns neither persistence
nor application effects.  A workflow-private READY root supplies the exact
already-owned objects; this module only validates their identity and issues a
single process-local proof after read-only predecessor validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Final, Literal, Protocol, cast

from manga_director.domain.state_machine import PageState
from manga_director.production.future_real_delivery_r25_attestation import (
    _R25CanonicalRecordV1,
    _R25ReplayFailureV1,
)
from manga_director.production.future_real_delivery_r25_trusted_pairing import (
    _R20ReplayFailureV1,
    _R25LocalFileCompositionV1,
    _r27_application_binding_identity,
    _require_exact_localfile_r25_composition_v1,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    LocalWorkflowApplicationLedgerStore,
    WorkflowApplicationLedgerBindingDTO,
    _canonical_payload,
    _consume_r26_authenticated_observation_for_proof_v1,
    _digest,
    _r26_protocol_digest,
    _R26AuthenticatedProtocolObservationV1,
)
from manga_director.repositories.local_file import LocalFileRepository

_R26_PROOF_FACTORY_ISSUER: Final = object()
_R26_PROOF_SEAL: Final = object()

_Outcome = Literal[
    "AUTHORITY_REJECTED",
    "LEGACY_PRE_ATTESTATION",
    "ALREADY_APPLIED",
    "RECOVERY_REQUIRED",
    "CORRUPT",
    "CONFLICT",
    "RECONCILIATION_INPUTS_REQUIRED",
    "SEALED_RECONCILIATION_PROOF_ISSUED",
    "CONSUMED",
    "RESTART_REQUIRED",
]


class _RevisionedSnapshotV1(Protocol):
    fingerprint: str
    revision: int


class _CurrentPageContextV1(Protocol):
    artifacts: dict[str, object]
    page: dict[str, object]
    state: PageState


class _AuthoritativePageStoreV1(Protocol):
    def context_from_snapshot(
        self, snapshot: _RevisionedSnapshotV1, page_id: str
    ) -> _CurrentPageContextV1: ...

    def load_revisioned(self, project_id: str) -> _RevisionedSnapshotV1: ...


@dataclass(frozen=True, slots=True)
class _R26ProofIssuanceResultV1:
    outcome: _Outcome
    proof: _AuthoritativePostCASReconciliationProofV1 | None = None


class _AuthoritativePostCASReconciliationProofV1:
    """Opaque one-shot proof for the future private Receipt boundary only."""

    __slots__ = ("_binding_digest", "_composition", "_invocation", "_nonce", "_post_identity", "_seal")

    _binding_digest: str
    _composition: _R25LocalFileCompositionV1
    _invocation: object
    _nonce: object
    _post_identity: tuple[int, str, str]
    _seal: object

    def __init__(self, *args: object) -> None:
        del args
        raise ValueError("AUTHORITY_REJECTED")

    def __copy__(self) -> _AuthoritativePostCASReconciliationProofV1:
        raise ValueError("AUTHORITY_REJECTED")

    def __deepcopy__(self, memo: dict[int, object]) -> _AuthoritativePostCASReconciliationProofV1:
        del memo
        raise ValueError("AUTHORITY_REJECTED")


class _PrivateConsumedR26ReceiptProjectionV1:
    """Opaque, one-shot private handoff from the R26 registry to Receipt."""

    __slots__ = ("_binding_digest", "_composition", "_invocation", "_nonce", "_seal")

    _binding_digest: str
    _composition: _R25LocalFileCompositionV1
    _invocation: object
    _nonce: object
    _seal: object

    def __init__(self, *args: object) -> None:
        del args
        raise ValueError("AUTHORITY_REJECTED")

    def __copy__(self) -> _PrivateConsumedR26ReceiptProjectionV1:
        raise ValueError("AUTHORITY_REJECTED")

    def __deepcopy__(self, memo: dict[int, object]) -> _PrivateConsumedR26ReceiptProjectionV1:
        del memo
        raise ValueError("AUTHORITY_REJECTED")


@dataclass(frozen=True, slots=True)
class _R26ConsumedReceiptProjectionResultV1:
    outcome: _Outcome
    projection: _PrivateConsumedR26ReceiptProjectionV1 | None = None


@dataclass(frozen=True, slots=True)
class _R26ReceiptProjectionFactsV1:
    """Registry-derived Receipt facts; no caller supplied value is authoritative."""

    outcome: _Outcome
    binding: WorkflowApplicationLedgerBindingDTO | None = None
    binding_digest: str | None = None
    output_asset_id: str | None = None
    post_commit_revision: int | None = None
    post_commit_fingerprint: str | None = None


class _R26ReconciliationProofFactoryV1:
    """Registry-held factory bound to one exact IMP-07A READY root."""

    __slots__ = ("_coordinator", "_issued", "_ledger_store", "_nonce", "_page_store", "_repository", "_root", "_r25")

    _coordinator: object
    _ledger_store: LocalWorkflowApplicationLedgerStore
    _nonce: object
    _page_store: _AuthoritativePageStoreV1
    _repository: LocalFileRepository
    _root: object
    _r25: _R25LocalFileCompositionV1
    _issued: set[_AuthoritativePostCASReconciliationProofV1]

    def __init__(self, *args: object) -> None:
        del args
        raise ValueError("AUTHORITY_REJECTED")


_FACTORIES: dict[_R26ReconciliationProofFactoryV1, tuple[object, ...]] = {}
_ROOT_FACTORIES: dict[object, _R26ReconciliationProofFactoryV1] = {}
_ISSUED: dict[_AuthoritativePostCASReconciliationProofV1, tuple[object, ...]] = {}
_CONSUMED: set[_AuthoritativePostCASReconciliationProofV1] = set()
_PROOFS_BY_INVOCATION: dict[object, _AuthoritativePostCASReconciliationProofV1] = {}
_RECEIPT_PROJECTIONS: dict[_PrivateConsumedR26ReceiptProjectionV1, tuple[object, ...]] = {}
# A consumed projection remains strongly retained only as a tombstone plus
# exact registry facts.  The facts are read-only and let the Coordinator bind
# its private post-consumption stage to the actual R26 consume transition.
_CONSUMED_RECEIPT_PROJECTIONS: dict[_PrivateConsumedR26ReceiptProjectionV1, tuple[object, ...]] = {}
_R26_REGISTRY_LOCK = RLock()


class _R26PredecessorFailureV1(ValueError):
    """Structured R26-local validation result, never inferred from exception text."""

    __slots__ = ("outcome",)

    outcome: Literal["CORRUPT", "CONFLICT"]

    def __init__(self, outcome: Literal["CORRUPT", "CONFLICT"]) -> None:
        super().__init__(outcome)
        self.outcome = outcome


def _construct_r26_reconciliation_proof_factory_v1(
    root: object,
    repository: object,
    coordinator: object,
    page_store: object,
    ledger_store: object,
    r25_composition: object,
    *,
    _issuer: object,
) -> _R26ReconciliationProofFactoryV1:
    """Attach one exact factory to the already authenticated READY root."""

    if _issuer is not _R26_PROOF_FACTORY_ISSUER or type(repository) is not LocalFileRepository:
        raise ValueError("AUTHORITY_REJECTED")
    if type(ledger_store) is not LocalWorkflowApplicationLedgerStore:
        raise ValueError("AUTHORITY_REJECTED")
    exact_r25 = _require_exact_localfile_r25_composition_v1(r25_composition, repository)
    if (
        getattr(root, "_repository", None) is not repository
        or getattr(root, "_ledger_store", None) is not ledger_store
        or getattr(root, "_composition", None) is None
        or getattr(getattr(root, "_composition", None), "external_application", None) is not coordinator
        or getattr(coordinator, "_page_store", None) is not page_store
        or getattr(page_store, "_repository", None) is not repository
        or getattr(coordinator, "_r25_localfile_composition", None) is not exact_r25
    ):
        raise ValueError("AUTHORITY_REJECTED")
    existing = _ROOT_FACTORIES.get(root)
    if existing is not None:
        issued = _FACTORIES.get(existing)
        if issued is None or not all(
            actual is expected
            for actual, expected in zip(
                issued, (root, repository, coordinator, page_store, ledger_store, exact_r25), strict=True
            )
        ):
            raise ValueError("CORRUPT")
        return existing
    factory = object.__new__(_R26ReconciliationProofFactoryV1)
    object.__setattr__(factory, "_root", root)
    object.__setattr__(factory, "_repository", repository)
    object.__setattr__(factory, "_coordinator", coordinator)
    object.__setattr__(factory, "_page_store", cast(_AuthoritativePageStoreV1, page_store))
    object.__setattr__(factory, "_ledger_store", ledger_store)
    object.__setattr__(factory, "_r25", exact_r25)
    object.__setattr__(factory, "_issued", set())
    object.__setattr__(factory, "_nonce", object())
    _FACTORIES[factory] = (root, repository, coordinator, page_store, ledger_store, exact_r25)
    _ROOT_FACTORIES[root] = factory
    return factory


def _issue_r26_reconciliation_proof_under_fence(  # noqa: C901
    factory: object,
    binding: object,
    observation: object,
    *,
    coordinator: object,
    page_store: object,
    invocation_authority: object,
) -> _R26ProofIssuanceResultV1:
    """Read authoritative predecessors and issue no more than one proof."""

    if type(factory) is not _R26ReconciliationProofFactoryV1 or type(binding) is not WorkflowApplicationLedgerBindingDTO:
        return _R26ProofIssuanceResultV1("AUTHORITY_REJECTED")
    issued = _FACTORIES.get(factory)
    if issued is None or issued[2] is not coordinator or issued[3] is not page_store:
        return _R26ProofIssuanceResultV1("AUTHORITY_REJECTED")
    try:
        if invocation_authority in _PROOFS_BY_INVOCATION:
            return _R26ProofIssuanceResultV1("AUTHORITY_REJECTED")
    except TypeError:
        return _R26ProofIssuanceResultV1("AUTHORITY_REJECTED")
    consume_invocation = getattr(coordinator, "_consume_r26_fence_invocation_authority_v1", None)
    if not callable(consume_invocation) or not consume_invocation(
        invocation_authority, factory, binding, page_store
    ):
        return _R26ProofIssuanceResultV1("AUTHORITY_REJECTED")
    if type(observation) is not _R26AuthenticatedProtocolObservationV1:
        return _R26ProofIssuanceResultV1("AUTHORITY_REJECTED")
    exact_observation = _consume_r26_authenticated_observation_for_proof_v1(
        observation, factory._ledger_store, factory._repository, factory._root, binding
    )
    if exact_observation is None:
        return _R26ProofIssuanceResultV1("AUTHORITY_REJECTED")
    if exact_observation.outcome == "APPLIED":
        return _R26ProofIssuanceResultV1("ALREADY_APPLIED")
    if exact_observation.outcome in {"MISSING", "RECOVERY_REQUIRED"}:
        return _R26ProofIssuanceResultV1("RECOVERY_REQUIRED")
    if exact_observation.outcome in {"CORRUPT"}:
        return _R26ProofIssuanceResultV1("CORRUPT")
    if exact_observation.outcome == "CONFLICT":
        return _R26ProofIssuanceResultV1("CONFLICT")
    if exact_observation.outcome == "AUTHORITY_REJECTED":
        return _R26ProofIssuanceResultV1("AUTHORITY_REJECTED")
    if exact_observation.outcome != "PREPARED":
        return _R26ProofIssuanceResultV1("RECONCILIATION_INPUTS_REQUIRED")
    binding_digest = _r27_application_binding_identity(binding)
    if exact_observation.marker_version == 0:
        return _R26ProofIssuanceResultV1("LEGACY_PRE_ATTESTATION")
    if (
        exact_observation.marker_version != 1
        or exact_observation.protocol_binding_digest != _r26_protocol_digest(_ledger_digest(binding), 1)
    ):
        return _R26ProofIssuanceResultV1("CORRUPT")
    try:
        r20 = factory._r25._r20_reader._replay_for_binding_v1(binding)
    except _R20ReplayFailureV1 as error:
        return _structured_predecessor_result(error.outcome)
    except ValueError:
        return _R26ProofIssuanceResultV1("CORRUPT")
    except Exception:
        return _R26ProofIssuanceResultV1("RECOVERY_REQUIRED")
    try:
        record = factory._r25._r25_store._replay_post_cas_attestation_exact_v1(binding_digest)
    except _R25ReplayFailureV1 as error:
        return _structured_predecessor_result(error.outcome)
    except ValueError:
        return _R26ProofIssuanceResultV1("CORRUPT")
    except Exception:
        return _R26ProofIssuanceResultV1("RECOVERY_REQUIRED")
    if record is None:
        return _R26ProofIssuanceResultV1("RECOVERY_REQUIRED")
    try:
        _validate_record(binding, r20, record)
        snapshot = factory._page_store.load_revisioned(binding.project_id)
        context = factory._page_store.context_from_snapshot(snapshot, binding.page_id)
        post_revision = cast(int, record.values[21])
        post_fingerprint = cast(str, record.values[22])
        if (
            context.state is not PageState.GENERATED
            or snapshot.revision != post_revision
            or snapshot.fingerprint != post_fingerprint
            or context.page.get("project_id") != binding.project_id
            or context.page.get("page_id") != binding.page_id
            or context.artifacts.get(PageState.GENERATED.value)
            != {"artifact_kind": "logical_output_asset", "output_asset_id": binding.output_asset_id}
        ):
            return _R26ProofIssuanceResultV1("RECOVERY_REQUIRED")
    except _R26PredecessorFailureV1 as error:
        return _structured_predecessor_result(error.outcome)
    except ValueError:
        return _R26ProofIssuanceResultV1("CORRUPT")
    except Exception:
        return _R26ProofIssuanceResultV1("RECOVERY_REQUIRED")
    proof = object.__new__(_AuthoritativePostCASReconciliationProofV1)
    object.__setattr__(proof, "_seal", _R26_PROOF_SEAL)
    object.__setattr__(proof, "_binding_digest", binding_digest)
    object.__setattr__(proof, "_nonce", factory._nonce)
    object.__setattr__(proof, "_post_identity", (post_revision, post_fingerprint, record.attestation_identity))
    object.__setattr__(proof, "_invocation", invocation_authority)
    object.__setattr__(proof, "_composition", factory._r25)
    # Preserve the exact R26-authenticated binding facts.  They are the sole
    # source for the later private Receipt projection.
    _ISSUED[proof] = (factory, invocation_authority, binding_digest, proof._post_identity, proof, binding)
    _PROOFS_BY_INVOCATION[invocation_authority] = proof
    factory._issued.add(proof)
    return _R26ProofIssuanceResultV1("SEALED_RECONCILIATION_PROOF_ISSUED", proof)


def _consume_r26_reconciliation_proof_for_receipt_v1(
    proof: object, factory: object, binding: object, *, invocation_authority: object
) -> _Outcome:
    """Compatibility-only private tombstone primitive for existing R26 tests."""

    consumed = _consume_r26_reconciliation_proof_into_receipt_projection_v1(
        proof, factory, binding, invocation_authority=invocation_authority
    )
    if consumed.outcome != "SEALED_RECONCILIATION_PROOF_ISSUED" or consumed.projection is None:
        return consumed.outcome
    facts = _consume_r26_receipt_projection_for_receipt_v1(
        consumed.projection,
        factory,
        binding,
        repository=getattr(factory, "_repository", None),
        composition=getattr(factory, "_r25", None),
        coordinator=getattr(factory, "_coordinator", None),
        invocation_authority=invocation_authority,
    )
    return "SEALED_RECONCILIATION_PROOF_ISSUED" if facts.outcome == "SEALED_RECONCILIATION_PROOF_ISSUED" else facts.outcome


def _consume_r26_reconciliation_proof_into_receipt_projection_v1(
    proof: object, factory: object, binding: object, *, invocation_authority: object
) -> _R26ConsumedReceiptProjectionResultV1:
    """Atomically exchange one exact proof for one registry-authenticated projection."""

    if type(proof) is not _AuthoritativePostCASReconciliationProofV1:
        return _R26ConsumedReceiptProjectionResultV1("AUTHORITY_REJECTED")
    if type(factory) is not _R26ReconciliationProofFactoryV1 or type(binding) is not WorkflowApplicationLedgerBindingDTO:
        return _R26ConsumedReceiptProjectionResultV1("AUTHORITY_REJECTED")
    with _R26_REGISTRY_LOCK:
        entry = _ISSUED.get(proof)
        if entry is None:
            return _R26ConsumedReceiptProjectionResultV1(
                "CONSUMED" if proof in _CONSUMED else "AUTHORITY_REJECTED"
            )
        if len(entry) != 6:
            return _R26ConsumedReceiptProjectionResultV1("CORRUPT")
        exact_binding = entry[5]
        if (
            type(exact_binding) is not WorkflowApplicationLedgerBindingDTO
            or entry[0] is not factory
            or entry[1] is not invocation_authority
            or entry[2] != _r27_application_binding_identity(exact_binding)
            or exact_binding != binding
            or proof._seal is not _R26_PROOF_SEAL
            or proof._nonce is not factory._nonce
            or proof._binding_digest != entry[2]
            or proof._invocation is not invocation_authority
            or proof._composition is not factory._r25
            or proof._post_identity is not entry[3]
            or entry[4] is not proof
            or not isinstance(entry[3], tuple)
            or len(entry[3]) != 3
            or not isinstance(entry[3][0], int)
            or isinstance(entry[3][0], bool)
            or entry[3][0] < 1
            or not _valid_private_fingerprint(entry[3][1])
        ):
            return _R26ConsumedReceiptProjectionResultV1("AUTHORITY_REJECTED")
        projection = object.__new__(_PrivateConsumedR26ReceiptProjectionV1)
        object.__setattr__(projection, "_seal", _R26_PROOF_SEAL)
        object.__setattr__(projection, "_binding_digest", entry[2])
        object.__setattr__(projection, "_nonce", factory._nonce)
        object.__setattr__(projection, "_invocation", invocation_authority)
        object.__setattr__(projection, "_composition", factory._r25)
        _RECEIPT_PROJECTIONS[projection] = (
            factory,
            invocation_authority,
            exact_binding,
            entry[2],
            entry[3][0],
            entry[3][1],
            factory._r25,
            projection,
        )
        _ISSUED.pop(proof)
        _CONSUMED.add(proof)
        if _PROOFS_BY_INVOCATION.get(invocation_authority) is proof:
            _PROOFS_BY_INVOCATION.pop(invocation_authority)
        factory._issued.discard(proof)
        return _R26ConsumedReceiptProjectionResultV1("SEALED_RECONCILIATION_PROOF_ISSUED", projection)


def _read_live_r26_receipt_projection_facts_for_confirmation_v1(
    projection: object,
    factory: object,
    binding: object,
    *,
    repository: object,
    composition: object,
    coordinator: object,
    invocation_authority: object,
) -> tuple[str, int, str] | None:
    """Read ordinary expected Receipt data from one exact still-live R26 projection."""

    if type(projection) is not _PrivateConsumedR26ReceiptProjectionV1:
        return None
    if type(factory) is not _R26ReconciliationProofFactoryV1 or type(binding) is not WorkflowApplicationLedgerBindingDTO:
        return None
    with _R26_REGISTRY_LOCK:
        entry = _RECEIPT_PROJECTIONS.get(projection)
        if entry is None or len(entry) != 8:
            return None
        exact_binding = entry[2]
        if (
            type(exact_binding) is not WorkflowApplicationLedgerBindingDTO
            or entry[0] is not factory
            or entry[1] is not invocation_authority
            or repository is not factory._repository
            or composition is not factory._r25
            or coordinator is not factory._coordinator
            or entry[6] is not composition
            or exact_binding != binding
            or entry[3] != _r27_application_binding_identity(exact_binding)
            or projection._seal is not _R26_PROOF_SEAL
            or projection._nonce is not factory._nonce
            or projection._binding_digest != entry[3]
            or projection._invocation is not invocation_authority
            or projection._composition is not composition
            or entry[7] is not projection
            or not isinstance(entry[4], int)
            or isinstance(entry[4], bool)
            or entry[4] < 1
            or not _valid_private_fingerprint(entry[5])
        ):
            return None
        return entry[3], entry[4], cast(str, entry[5])


def _consume_r26_receipt_projection_for_receipt_v1(
    projection: object,
    factory: object,
    binding: object,
    *,
    repository: object,
    composition: object,
    coordinator: object,
    invocation_authority: object,
) -> _R26ReceiptProjectionFactsV1:
    """Consume exact projection authority before fallible Receipt persistence."""

    if type(projection) is not _PrivateConsumedR26ReceiptProjectionV1:
        return _R26ReceiptProjectionFactsV1("AUTHORITY_REJECTED")
    if type(factory) is not _R26ReconciliationProofFactoryV1 or type(binding) is not WorkflowApplicationLedgerBindingDTO:
        return _R26ReceiptProjectionFactsV1("AUTHORITY_REJECTED")
    with _R26_REGISTRY_LOCK:
        entry = _RECEIPT_PROJECTIONS.get(projection)
        if entry is None:
            return _R26ReceiptProjectionFactsV1(
                "CONSUMED" if projection in _CONSUMED_RECEIPT_PROJECTIONS else "AUTHORITY_REJECTED"
            )
        if len(entry) != 8:
            return _R26ReceiptProjectionFactsV1("CORRUPT")
        exact_binding = entry[2]
        if (
            type(exact_binding) is not WorkflowApplicationLedgerBindingDTO
            or entry[0] is not factory
            or entry[1] is not invocation_authority
            or repository is not factory._repository
            or composition is not factory._r25
            or coordinator is not factory._coordinator
            or entry[6] is not composition
            or exact_binding != binding
            or entry[3] != _r27_application_binding_identity(exact_binding)
            or projection._seal is not _R26_PROOF_SEAL
            or projection._nonce is not factory._nonce
            or projection._binding_digest != entry[3]
            or projection._invocation is not invocation_authority
            or projection._composition is not composition
            or entry[7] is not projection
            or exact_binding.output_asset_id != binding.output_asset_id
            or not isinstance(entry[4], int)
            or isinstance(entry[4], bool)
            or entry[4] < 1
            or not _valid_private_fingerprint(entry[5])
        ):
            return _R26ReceiptProjectionFactsV1("AUTHORITY_REJECTED")
        _RECEIPT_PROJECTIONS.pop(projection)
        _CONSUMED_RECEIPT_PROJECTIONS[projection] = entry
        return _R26ReceiptProjectionFactsV1(
            "SEALED_RECONCILIATION_PROOF_ISSUED",
            binding=exact_binding,
            binding_digest=entry[3],
            output_asset_id=exact_binding.output_asset_id,
            post_commit_revision=entry[4],
            post_commit_fingerprint=cast(str, entry[5]),
        )


def _read_consumed_r26_receipt_projection_facts_for_confirmation_v1(
    projection: object,
    factory: object,
    binding: object,
    *,
    repository: object,
    composition: object,
    coordinator: object,
    invocation_authority: object,
) -> tuple[str, int, str] | None:
    """Read facts only from one exact already-consumed projection tombstone."""

    if type(projection) is not _PrivateConsumedR26ReceiptProjectionV1:
        return None
    if type(factory) is not _R26ReconciliationProofFactoryV1 or type(binding) is not WorkflowApplicationLedgerBindingDTO:
        return None
    with _R26_REGISTRY_LOCK:
        entry = _CONSUMED_RECEIPT_PROJECTIONS.get(projection)
        if entry is None or len(entry) != 8:
            return None
        exact_binding = entry[2]
        if (
            type(exact_binding) is not WorkflowApplicationLedgerBindingDTO
            or entry[0] is not factory
            or entry[1] is not invocation_authority
            or repository is not factory._repository
            or composition is not factory._r25
            or coordinator is not factory._coordinator
            or entry[6] is not composition
            or exact_binding != binding
            or entry[3] != _r27_application_binding_identity(exact_binding)
            or projection._seal is not _R26_PROOF_SEAL
            or projection._nonce is not factory._nonce
            or projection._binding_digest != entry[3]
            or projection._invocation is not invocation_authority
            or projection._composition is not composition
            or entry[7] is not projection
            or not isinstance(entry[4], int)
            or isinstance(entry[4], bool)
            or entry[4] < 1
            or not _valid_private_fingerprint(entry[5])
        ):
            return None
        return entry[3], entry[4], cast(str, entry[5])


def _ledger_digest(binding: WorkflowApplicationLedgerBindingDTO) -> str:
    """Use the Ledger's canonical DTO payload rather than caller equality."""
    return _digest(_canonical_payload(binding, "prepared"))


def _valid_private_fingerprint(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _validate_record(binding: WorkflowApplicationLedgerBindingDTO, r20: object, record: _R25CanonicalRecordV1) -> None:
    values = record.values
    if len(values) != 28 or values[3] != _r27_application_binding_identity(binding):
        raise _R26PredecessorFailureV1("CORRUPT")
    if (
        values[1] != getattr(r20, "delivery_identity", None)
        or values[2] != binding.attempt_id
        or values[4] != binding.project_id
        or values[5] != binding.page_id
        or values[6] != binding.target_page_reference or values[7] != binding.provider_reference
        or values[8] != binding.authorization_id or values[9] != binding.output_asset_id
        or values[10] != getattr(r20, "canonical_result_identity", None)
        or values[11] != getattr(r20, "logical_output_id", None)
        or values[12] != getattr(r20, "asset_id", None) or values[13] != getattr(r20, "asset_sha256", None)
        or values[14] != getattr(r20, "expected_byte_length", None)
        or values[15] != getattr(r20, "media_type", None)
        or values[16] != getattr(r20, "evidence_identity", None)
        or values[17] != getattr(r20, "evidence_persistence_identity", None)
        or values[18] != getattr(r20, "binding_digest", None)
        or values[19] != getattr(r20, "historical_page_revision", None)
        or values[20] != getattr(r20, "historical_page_fingerprint", None)
        or values[23] != "PromptBuilt" or values[24] != "Generated"
    ):
        raise _R26PredecessorFailureV1("CONFLICT")


def _structured_predecessor_result(
    outcome: Literal["AUTHORITY_REJECTED", "CORRUPT", "CONFLICT", "NOT_FOUND", "RECOVERY_REQUIRED"],
) -> _R26ProofIssuanceResultV1:
    return _R26ProofIssuanceResultV1(
        cast(_Outcome, "RECOVERY_REQUIRED" if outcome in {"NOT_FOUND", "RECOVERY_REQUIRED"} else outcome)
    )
