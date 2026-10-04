"""Private LocalFile application of an already durable generated output.

This module deliberately owns neither generation nor assets.  It bridges an
already eligible Evidence chain to the existing fenced LocalFile page commit
path, using the Workflow Application Ledger as the immutable application
proof.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from threading import RLock
from typing import Literal, Protocol, cast

from manga_director.domain.events import EventType, WorkflowEvent
from manga_director.domain.project import Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events.bus import EventBus
from manga_director.production.future_real_delivery_r25_trusted_pairing import (
    _construct_localfile_r25_composition_v1,
    _consume_r30_restart_ingress_and_materialize_v1,
    _issue_r30_restart_ingress_v1,
    _materialize_normal_r25_v1,
    _record_normal_r30_pre_cas_provenance_v1,
    _require_exact_localfile_r25_composition_v1,
)
from manga_director.production.future_real_delivery_r26_reconciliation import (
    _consume_r26_reconciliation_proof_into_receipt_projection_v1,
    _issue_r26_reconciliation_proof_under_fence,
    _read_consumed_r26_receipt_projection_facts_for_confirmation_v1,
)
from manga_director.production.next_generation_durable_application_commit_receipt import (
    DurableApplicationCommitReceiptService,
    DurableApplicationCommitReceiptStorePort,
    LocalDurableApplicationCommitReceiptStore,
    _receipt,
)
from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    DurableEvidenceWorkflowBindingReport,
    WorkflowApplicationAuthorizationDTO,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    _R26_FINALIZER_ISSUER,
    LocalWorkflowApplicationLedgerStore,
    WorkflowApplicationLedgerBindingDTO,
    WorkflowApplicationLedgerService,
    WorkflowApplicationLedgerStorePort,
    _authoritative_commit_proof,
    _binding_from_eligibility,
    _finalize_r26_ledger_reconciliation_v1,
    _issue_r26_ledger_finalizer_authorization_v1,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.local_file_aggregate_envelope import _decode_r27_aggregate
from manga_director.repositories.local_file_durability import (
    LocalFileDurabilityError,
    RevisionedProjectSnapshot,
    _R27CommittedRecord,
    _R27PreparedRecord,
)
from manga_director.workflow.contracts import WorkflowContext
from manga_director.workflow.durable_execution import (
    DurablePageStorePort,
    LocalFileDurablePageStore,
    _R27PublicationIntent,
)
from manga_director.workflow.page_execution_fence import (
    PageExecutionFenceError,
    PageExecutionFencePort,
    WindowsPageExecutionFence,
)

ExternalApplicationStatus = Literal[
    "application_not_applied",
    "application_applied_event_published",
    "application_applied_event_failed",
    "application_applied_ledger_finalize_failed",
    "application_applied_receipt_failed",
    "application_replay_confirmed",
]
_FENCE_CONTEXT_ISSUER = object()
_R27_FACTORY_ISSUER = object()


class _R27PublicationIntentFactory:
    """Private canonical-coordinator issuer for the R28 test-only handoff."""

    def __init__(self, pair: object, *, _issuer: object) -> None:
        if _issuer is not _R27_FACTORY_ISSUER:
            raise ValueError("r27 publication factory is private")
        self._pair = pair
        self._issued_intents: dict[int, _R27PublicationIntent] = {}

    def _issue(
        self,
        binding: WorkflowApplicationLedgerBindingDTO,
        snapshot: RevisionedProjectSnapshot,
        context: WorkflowContext,
        project: Project,
    ) -> _R27PublicationIntent:
        if (
            context.state is not PageState.PROMPT_BUILT
            or binding.project_id != snapshot.project.id
            or context.page.get("project_id") != binding.project_id
            or context.page.get("page_id") != binding.page_id
            or getattr(project, "id", None) != binding.project_id
        ):
            raise ValueError("r27 publication factory input is invalid")
        intent = _R27PublicationIntent(
            pair=self._pair,
            application_binding_identity=_r27_application_binding_identity(binding),
            attempt_id=binding.attempt_id,
            project_id=binding.project_id,
            page_id=binding.page_id,
            target_page_reference=binding.target_page_reference,
            source_state=binding.source_state,
            target_state=binding.target_state,
            expected_revision=snapshot.revision,
            expected_aggregate_fingerprint=snapshot.fingerprint,
        )
        self._issued_intents[id(intent)] = intent
        return intent

    def _consume_issued(self, intent: _R27PublicationIntent) -> bool:
        """Consume only the exact factory-issued object before durable publication."""

        key = id(intent)
        if self._issued_intents.get(key) is not intent:
            return False
        del self._issued_intents[key]
        return True


class _R27ProjectActivationPolicy:
    """Private format-selection decision beside the canonical Coordinator.

    This object observes only LocalFile's authoritative aggregate and private
    durability sidecars.  It creates no state, request, or CAS capability.
    RevisionStore rechecks the selected raw state under its project fence.
    """

    def __init__(self, repository: LocalFileRepository) -> None:
        self._repository = repository

    def _select_first_publication(self, binding: WorkflowApplicationLedgerBindingDTO) -> bool:
        project_id = binding.project_id
        try:
            aggregate = self._repository._path(project_id).read_bytes()
            framed = _decode_r27_aggregate(aggregate)
            activation = self._repository._revision_store._read_r29_activation(project_id)
            prepared = self._repository._revision_store._read_prepared_for(project_id)
            committed = self._repository._revision_store._read_committed(project_id)
        except (OSError, ValueError, LocalFileDurabilityError) as exc:
            raise LocalFileDurabilityError("r29_activation_selection_invalid") from exc

        if framed is None:
            if activation is not None:
                raise LocalFileDurabilityError("r29_activation_recovery_required")
            if isinstance(prepared, _R27PreparedRecord) or isinstance(committed, _R27CommittedRecord):
                raise LocalFileDurabilityError("r29_activation_selection_invalid")
            return True
        if activation is not None and activation.state == "R27_COMMITTED":
            return False
        raise LocalFileDurabilityError("r29_activation_selection_invalid")


def _r27_application_binding_identity(binding: WorkflowApplicationLedgerBindingDTO) -> str:
    """Derive the frozen application-binding identity from authoritative facts."""

    body: dict[str, str | int] = {
        "application_binding_identity": "",
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
    return _r27_digest(
        {key: value for key, value in body.items() if key != "application_binding_identity"}
    )


def _r27_digest(value: Mapping[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, allow_nan=False).encode(
            "utf-8"
        )
    ).hexdigest()


def _r27_intent_matches_authoritative_facts(
    intent: object,
    factory: _R27PublicationIntentFactory,
    binding: WorkflowApplicationLedgerBindingDTO,
    snapshot: RevisionedProjectSnapshot,
) -> bool:
    """Reject a malformed factory handoff before R27 PREPARED durability."""

    return (
        type(intent) is _R27PublicationIntent
        and intent.pair is factory._pair
        and intent.application_binding_identity == _r27_application_binding_identity(binding)
        and intent.attempt_id == binding.attempt_id
        and intent.project_id == binding.project_id == snapshot.project.id
        and intent.page_id == binding.page_id
        and intent.target_page_reference == binding.target_page_reference
        and intent.source_state == binding.source_state == PageState.PROMPT_BUILT.value
        and intent.target_state == binding.target_state == PageState.GENERATED.value
        and intent.expected_revision == snapshot.revision
        and intent.expected_aggregate_fingerprint == snapshot.fingerprint
    )


@dataclass(frozen=True, slots=True)
class ExternalGeneratedApplicationResult:
    """Redacted private result for one externally generated page application."""

    project_id: str
    page_id: str
    status: ExternalApplicationStatus
    code: str
    event_published: bool


class _ExternalApplicationLease(Protocol):
    """Private resource retained from in-fence admission through canonical CAS."""

    def release(self) -> None: ...


@dataclass(frozen=True, slots=True)
class _ExternalApplicationGuardDecision:
    """Private non-authoritative result of one optional in-fence D10 guard."""

    allowed: bool
    code: str
    lease: _ExternalApplicationLease | None = None


class _ExternalApplicationPreApplyGuardPort(Protocol):
    """Private read-only guard; it cannot receive page mutation capabilities."""

    def validate(
        self,
        binding: WorkflowApplicationLedgerBindingDTO,
        snapshot: RevisionedProjectSnapshot,
        context: WorkflowContext,
        fence_context: _ExternalApplicationFenceContext,
    ) -> _ExternalApplicationGuardDecision: ...


@dataclass(frozen=True, slots=True, eq=False)
class _ExternalApplicationFenceContext:
    """One private, coordinator-created validation context for a held page fence."""

    project_id: str
    page_id: str
    target_page_reference: str
    revision: int
    fingerprint: str
    _issuer: object = field(repr=False, compare=False)
    _attempt_token: object = field(repr=False, compare=False)

    @classmethod
    def _create(
        cls,
        binding: WorkflowApplicationLedgerBindingDTO,
        snapshot: RevisionedProjectSnapshot,
    ) -> _ExternalApplicationFenceContext:
        return cls(
            project_id=binding.project_id,
            page_id=binding.page_id,
            target_page_reference=binding.target_page_reference,
            revision=snapshot.revision,
            fingerprint=snapshot.fingerprint,
            _issuer=_FENCE_CONTEXT_ISSUER,
            _attempt_token=object(),
        )

    def _matches(
        self,
        binding: WorkflowApplicationLedgerBindingDTO,
        snapshot: RevisionedProjectSnapshot,
        context: WorkflowContext,
    ) -> bool:
        return (
            self._issuer is _FENCE_CONTEXT_ISSUER
            and self.project_id == binding.project_id == context.page.get("project_id")
            and self.page_id == binding.page_id == context.page.get("page_id")
            and self.target_page_reference == binding.target_page_reference
            and self.revision == snapshot.revision
            and self.fingerprint == snapshot.fingerprint
        )


class _R26FenceInvocationAuthorityV1:
    """Opaque one-use attestation of the existing canonical page fence."""

    __slots__ = ("_binding", "_coordinator", "_fence", "_fence_context", "_page_store", "_used")

    _binding: WorkflowApplicationLedgerBindingDTO
    _coordinator: LocalFileExternalGeneratedApplicationCoordinator
    _fence: PageExecutionFencePort
    _fence_context: _ExternalApplicationFenceContext
    _page_store: DurablePageStorePort
    _used: bool

    def __init__(self, *args: object) -> None:
        del args
        raise ValueError("AUTHORITY_REJECTED")

    def __copy__(self) -> _R26FenceInvocationAuthorityV1:
        raise ValueError("AUTHORITY_REJECTED")

    def __deepcopy__(self, memo: dict[int, object]) -> _R26FenceInvocationAuthorityV1:
        del memo
        raise ValueError("AUTHORITY_REJECTED")


class _ExactReceiptReconciliationConfirmationV1:
    """Opaque IMP-09 output reserved for the later private IMP-10 inlet."""

    __slots__ = ("_seal",)

    _seal: object

    def __init__(self, *args: object) -> None:
        del args
        raise ValueError("AUTHORITY_REJECTED")

    def __copy__(self) -> _ExactReceiptReconciliationConfirmationV1:
        raise ValueError("AUTHORITY_REJECTED")

    def __deepcopy__(self, memo: dict[int, object]) -> _ExactReceiptReconciliationConfirmationV1:
        del memo
        raise ValueError("AUTHORITY_REJECTED")


class LocalFileLogicalOutputAssetQualityGate:
    """Require one exact applied Ledger proof before Quality can inspect a logical asset."""

    def __init__(
        self,
        ledger_service: WorkflowApplicationLedgerService,
        ledger_store: WorkflowApplicationLedgerStorePort,
    ) -> None:
        self._ledger_service = ledger_service
        self._ledger_store = ledger_store

    def require_applied(self, context: WorkflowContext) -> str | None:
        values = _logical_output_values(context)
        if values is None:
            return "LOGICAL_OUTPUT_ASSET_QUALITY_PROOF_INVALID"
        project_id, page_id, output_asset_id = values
        report = self._ledger_service.lookup_applied(
            project_id, page_id, output_asset_id, self._ledger_store
        )
        if (
            report.status == "applied"
            and report.applied is True
            and report.binding is not None
            and _binding_matches(report.binding, project_id, page_id, output_asset_id)
        ):
            return None
        return "LOGICAL_OUTPUT_ASSET_QUALITY_PROOF_UNAVAILABLE"


class LocalFileExternalGeneratedApplicationCoordinator:
    """Apply one immutable external result without an Agent or provider invocation."""

    def __init__(
        self,
        state_machine: StateMachine,
        event_bus: EventBus,
        ledger_service: WorkflowApplicationLedgerService,
        ledger_store: WorkflowApplicationLedgerStorePort,
        receipt_service: DurableApplicationCommitReceiptService,
        receipt_store: DurableApplicationCommitReceiptStorePort,
        page_store: DurablePageStorePort,
        *,
        fence_factory: Callable[[str, str], PageExecutionFencePort] = WindowsPageExecutionFence,
        pre_apply_guard: _ExternalApplicationPreApplyGuardPort | None = None,
        _r27_publication_factory: _R27PublicationIntentFactory | None = None,
    ) -> None:
        self._state_machine = state_machine
        self._event_bus = event_bus
        self._ledger_service = ledger_service
        self._ledger_store = ledger_store
        self._receipt_service = receipt_service
        self._receipt_store = receipt_store
        self._page_store = page_store
        self._fence_factory = fence_factory
        self._pre_apply_guard = pre_apply_guard
        self._r27_publication_factory = _r27_publication_factory
        self._r29_activation_policy: _R27ProjectActivationPolicy | None = None
        self._r25_localfile_composition: object | None = None
        self._r26_proof_factory: object | None = None
        self._r26_ledger_finalizer: object | None = None
        self._r26_ledger_finalizer_authorization: object | None = None
        self._r26_active_fence_contexts: set[_ExternalApplicationFenceContext] = set()
        self._r26_fence_invocations: set[_R26FenceInvocationAuthorityV1] = set()
        self._r26_fence_invocations_by_context: dict[
            _ExternalApplicationFenceContext, _R26FenceInvocationAuthorityV1
        ] = {}
        self._r26_receipt_confirmations: set[_ExactReceiptReconciliationConfirmationV1] = set()
        self._r26_consuming_receipt_confirmations: set[_ExactReceiptReconciliationConfirmationV1] = set()
        self._r26_consumed_receipt_confirmations: set[_ExactReceiptReconciliationConfirmationV1] = set()
        self._r26_receipt_confirmation_records: dict[
            _ExactReceiptReconciliationConfirmationV1, tuple[object, ...]
        ] = {}
        self._r26_pending_receipt_confirmations: dict[
            _R26FenceInvocationAuthorityV1, tuple[object, ...]
        ] = {}
        # Ordinary Coordinator lifecycle state, not transferable authority:
        # one exact invocation may permanently mint at most one confirmation.
        self._r26_terminal_receipt_confirmation_invocations: set[
            _R26FenceInvocationAuthorityV1
        ] = set()
        self._r26_receipt_confirmation_lock = RLock()
        if _r27_publication_factory is not None:
            if (
                type(page_store) is not LocalFileDurablePageStore
                or page_store._r27_pair is not _r27_publication_factory._pair
            ):
                raise ValueError("r27 publication requires LocalFile private composition")

    def apply(
        self,
        binding_report: DurableEvidenceWorkflowBindingReport,
        authorization: WorkflowApplicationAuthorizationDTO,
    ) -> ExternalGeneratedApplicationResult:
        """Apply only an exact, eligible, authorized external generated result."""

        if self._r25_localfile_composition is not None:
            binding = _binding_from_eligibility(binding_report, authorization)
            if binding is None:
                return _not_applied(
                    _result_identity(binding_report), "EXTERNAL_APPLICATION_LEDGER_PREPARE_BLOCKED"
                )
            return self._apply_r30_aware(binding, binding_report, authorization)
        prepared = self._ledger_service.prepare(binding_report, authorization, self._ledger_store)
        binding = prepared.binding
        if prepared.status == "blocked" or binding is None:
            return _not_applied(_result_identity(binding_report), "EXTERNAL_APPLICATION_LEDGER_PREPARE_BLOCKED")
        if prepared.applied is True:
            return self._confirm_applied_replay(binding)
        if prepared.prepared is not True:
            return _not_applied(_result_identity(binding_report), "EXTERNAL_APPLICATION_LEDGER_PREPARE_INVALID")
        return self._apply_prepared(binding)

    def _apply_r30_aware(
        self,
        binding: WorkflowApplicationLedgerBindingDTO,
        binding_report: DurableEvidenceWorkflowBindingReport,
        authorization: WorkflowApplicationAuthorizationDTO,
    ) -> ExternalGeneratedApplicationResult:
        """Keep R30 normal preparation within the existing canonical page fence."""

        fence: PageExecutionFencePort | None = None
        fence_context: _ExternalApplicationFenceContext | None = None
        lease: _ExternalApplicationLease | None = None
        r26_invocation: _R26FenceInvocationAuthorityV1 | None = None
        try:
            fence = self._fence_factory(binding.project_id, binding.page_id)
            fence.acquire()
            snapshot = self._page_store.load_revisioned(binding.project_id)
            context = self._page_store.context_from_snapshot(snapshot, binding.page_id)
            fence_context = _ExternalApplicationFenceContext._create(binding, snapshot)
            lease, early_result = self._r30_validate_fenced_context(
                binding, snapshot, context, fence_context
            )
            if early_result is not None:
                return early_result
            if self._r26_proof_factory is not None:
                if fence is None:
                    return _not_applied(binding, "EXTERNAL_APPLICATION_PAGE_FENCE_UNAVAILABLE")
                self._r26_active_fence_contexts.add(fence_context)
                r26_invocation = self._issue_r26_fence_invocation_authority_v1(
                    binding, fence, fence_context
                )
            if context.state == PageState.GENERATED:
                return self._materialize_r30_restart_under_fence(
                    binding, binding_report, authorization, r26_invocation
                )
            if context.state != PageState.PROMPT_BUILT:
                return _not_applied(binding, "EXTERNAL_APPLICATION_SOURCE_STATE_MISMATCH")
            return self._r30_prepare_and_commit_under_fence(
                binding, binding_report, authorization, snapshot, context
            )
        except PageExecutionFenceError:
            return _not_applied(binding, "EXTERNAL_APPLICATION_PAGE_FENCE_UNAVAILABLE")
        except Exception:
            return _not_applied(binding, "EXTERNAL_APPLICATION_FAILED")
        finally:
            if r26_invocation is not None:
                self._tombstone_r26_fence_invocation_authority_v1(r26_invocation)
            if fence_context is not None:
                self._r26_active_fence_contexts.discard(fence_context)
            if lease is not None:
                lease.release()
            if fence is not None:
                fence.release()

    def _r30_validate_fenced_context(
        self,
        binding: WorkflowApplicationLedgerBindingDTO,
        snapshot: RevisionedProjectSnapshot,
        context: WorkflowContext,
        fence_context: _ExternalApplicationFenceContext,
    ) -> tuple[_ExternalApplicationLease | None, ExternalGeneratedApplicationResult | None]:
        lease, guard_error = self._acquire_guard_lease(binding, snapshot, context, fence_context)
        if guard_error is not None:
            return lease, _not_applied(binding, guard_error)
        return lease, None

    def _issue_r26_fence_invocation_authority_v1(
        self,
        binding: WorkflowApplicationLedgerBindingDTO,
        fence: PageExecutionFencePort,
        fence_context: _ExternalApplicationFenceContext,
    ) -> _R26FenceInvocationAuthorityV1:
        """Attest the already-held canonical fence without creating another fence."""

        if (
            self._r26_proof_factory is None
            or type(fence_context) is not _ExternalApplicationFenceContext
            or fence_context._issuer is not _FENCE_CONTEXT_ISSUER
            or fence_context.project_id != binding.project_id
            or fence_context.page_id != binding.page_id
            or fence_context.target_page_reference != binding.target_page_reference
            or fence_context not in self._r26_active_fence_contexts
            or type(fence) is not WindowsPageExecutionFence
            or not fence._r26_is_held_for(binding.project_id, binding.page_id)
        ):
            raise ValueError("AUTHORITY_REJECTED")
        existing = self._r26_fence_invocations_by_context.get(fence_context)
        if existing is not None:
            if existing in self._r26_fence_invocations and existing._used is False:
                raise ValueError("AUTHORITY_REJECTED")
            raise ValueError("CORRUPT")
        authority = object.__new__(_R26FenceInvocationAuthorityV1)
        object.__setattr__(authority, "_binding", binding)
        object.__setattr__(authority, "_coordinator", self)
        object.__setattr__(authority, "_fence", fence)
        object.__setattr__(authority, "_fence_context", fence_context)
        object.__setattr__(authority, "_page_store", self._page_store)
        object.__setattr__(authority, "_used", False)
        self._r26_fence_invocations.add(authority)
        self._r26_fence_invocations_by_context[fence_context] = authority
        return authority

    def _consume_r26_fence_invocation_authority_v1(
        self,
        authority: object,
        factory: object,
        binding: object,
        page_store: object,
    ) -> bool:
        """Consume only the exact live in-fence authority for this Coordinator call."""

        if (
            type(authority) is not _R26FenceInvocationAuthorityV1
            or type(binding) is not WorkflowApplicationLedgerBindingDTO
            or authority not in self._r26_fence_invocations
            or self._r26_fence_invocations_by_context.get(authority._fence_context) is not authority
            or authority._coordinator is not self
            or authority._binding is not binding
            or authority._page_store is not page_store
            or page_store is not self._page_store
            or self._r26_proof_factory is not factory
            or authority._fence_context._issuer is not _FENCE_CONTEXT_ISSUER
            or authority._fence_context.project_id != binding.project_id
            or authority._fence_context.page_id != binding.page_id
            or authority._fence_context.target_page_reference != binding.target_page_reference
            or authority._fence_context not in self._r26_active_fence_contexts
            or type(authority._fence) is not WindowsPageExecutionFence
            or not authority._fence._r26_is_held_for(binding.project_id, binding.page_id)
            or authority._used is not False
        ):
            return False
        self._r26_fence_invocations.remove(authority)
        self._r26_fence_invocations_by_context.pop(authority._fence_context, None)
        object.__setattr__(authority, "_used", True)
        return True

    def _tombstone_r26_fence_invocation_authority_v1(
        self, authority: _R26FenceInvocationAuthorityV1
    ) -> None:
        self._discard_r26_pending_receipt_confirmation_v1(authority)
        self._r26_fence_invocations.discard(authority)
        if self._r26_fence_invocations_by_context.get(authority._fence_context) is authority:
            self._r26_fence_invocations_by_context.pop(authority._fence_context)
        object.__setattr__(authority, "_used", True)

    def _materialize_r30_restart_under_fence(  # noqa: C901
        self,
        binding: WorkflowApplicationLedgerBindingDTO,
        binding_report: DurableEvidenceWorkflowBindingReport,
        authorization: WorkflowApplicationAuthorizationDTO,
        r26_invocation: object | None,
    ) -> ExternalGeneratedApplicationResult:
        """Use the frozen sidecar/read-only gate before any restart Ledger mutation."""

        composition = self._r25_localfile_composition
        if composition is None or type(self._page_store) is not LocalFileDurablePageStore:
            return _not_applied(binding, "EXTERNAL_APPLICATION_PREPARED_GENERATED_AMBIGUOUS")
        if type(self._ledger_store) is not LocalWorkflowApplicationLedgerStore:
            return _not_applied(binding, "EXTERNAL_APPLICATION_PREPARED_GENERATED_AMBIGUOUS")
        observation = self._ledger_store._observe_exact_readonly_v1(binding)
        if observation.outcome == "APPLIED":
            snapshot = self._page_store.load_revisioned(binding.project_id)
            context = self._page_store.context_from_snapshot(snapshot, binding.page_id)
            return self._confirm_applied_replay_under_fence(binding, context)
        try:
            ingress = _issue_r30_restart_ingress_v1(
                composition, self._page_store._repository, binding, observation
            )
        except ValueError:
            return _not_applied(binding, "EXTERNAL_APPLICATION_PREPARED_GENERATED_AMBIGUOUS")
        materialization_confirmation = self._ledger_service.prepare(
            binding_report, authorization, self._ledger_store
        )
        try:
            materialized = _consume_r30_restart_ingress_and_materialize_v1(
                composition, self._page_store._repository, ingress, materialization_confirmation
            )
        except ValueError:
            materialized = False
        if not materialized:
            return _not_applied(binding, "EXTERNAL_APPLICATION_RESTART_R25_MATERIALIZATION_FAILED")
        factory = self._r26_proof_factory
        if factory is None:
            return _not_applied(binding, "EXTERNAL_APPLICATION_RESTART_R25_MATERIALIZED")
        if r26_invocation is None:
            return _not_applied(binding, "EXTERNAL_APPLICATION_PREPARED_GENERATED_AMBIGUOUS")
        root = getattr(factory, "_root", None)
        if root is None:
            return _not_applied(binding, "EXTERNAL_APPLICATION_PREPARED_GENERATED_AMBIGUOUS")
        r26_observation = root._observe_r26_protocol_marker_v2(binding)
        issuance = _issue_r26_reconciliation_proof_under_fence(
            factory,
            binding,
            r26_observation,
            coordinator=self,
            page_store=self._page_store,
            invocation_authority=r26_invocation,
        )
        if issuance.outcome != "SEALED_RECONCILIATION_PROOF_ISSUED":
            return _not_applied(binding, f"EXTERNAL_APPLICATION_R26_{issuance.outcome}")
        if issuance.proof is None or type(self._page_store) is not LocalFileDurablePageStore:
            return _not_applied(binding, "EXTERNAL_APPLICATION_R26_CORRUPT")
        projection = _consume_r26_reconciliation_proof_into_receipt_projection_v1(
            issuance.proof, factory, binding, invocation_authority=r26_invocation
        )
        if (
            projection.outcome != "SEALED_RECONCILIATION_PROOF_ISSUED"
            or projection.projection is None
        ):
            return _not_applied(binding, f"EXTERNAL_APPLICATION_R26_{projection.outcome}")
        receipt = self._receipt_service._commit_consumed_r26_projection_v1(
            projection.projection,
            factory,
            binding,
            repository=self._page_store._repository,
            composition=composition,
            coordinator=self,
            invocation_authority=r26_invocation,
            receipt_store=self._receipt_store,
        )
        if receipt.outcome != "RECEIPT_CONFIRMED":
            self._discard_r26_pending_receipt_confirmation_v1(r26_invocation)
            return _not_applied(binding, f"EXTERNAL_APPLICATION_R26_RECEIPT_{receipt.outcome}")
        if not self._record_r26_pending_receipt_confirmation_v1(
            factory, binding, composition, r26_invocation, projection.projection
        ):
            return _not_applied(binding, "EXTERNAL_APPLICATION_R26_RECEIPT_RECOVERY_REQUIRED")
        confirmation = self._issue_exact_receipt_reconciliation_confirmation_v1(
            factory, binding, composition, r26_invocation
        )
        if confirmation is None:
            return _not_applied(binding, "EXTERNAL_APPLICATION_R26_RECEIPT_RECOVERY_REQUIRED")
        prepared_observation = root._observe_r26_protocol_marker_v2(binding)
        if getattr(prepared_observation, "outcome", None) == "APPLIED":
            outcome = self._begin_r26_receipt_confirmation_consumption_v1(
                confirmation, factory, binding, composition, r26_invocation
            )
            if outcome == "CONSUMING":
                self._tombstone_r26_receipt_confirmation_v1(confirmation)
                return _not_applied(binding, "EXTERNAL_APPLICATION_R26_ALREADY_APPLIED")
            return _not_applied(binding, f"EXTERNAL_APPLICATION_R26_{outcome}")
        outcome = self._finalize_r26_ledger_from_confirmation_v1(
            confirmation,
            factory,
            binding,
            composition,
            r26_invocation,
            prepared_observation,
        )
        return _not_applied(binding, f"EXTERNAL_APPLICATION_R26_{outcome}")

    def _issue_exact_receipt_reconciliation_confirmation_v1(
        self,
        factory: object,
        binding: WorkflowApplicationLedgerBindingDTO,
        composition: object,
        invocation_authority: object,
    ) -> _ExactReceiptReconciliationConfirmationV1 | None:
        """Confirm one exact Receipt from this Coordinator's retained R26 context."""

        if type(self._page_store) is not LocalFileDurablePageStore:
            return None
        candidate = self._r26_pending_receipt_confirmation_v1(
            factory, binding, composition, invocation_authority
        )
        if candidate is None:
            return None
        exact_invocation = cast(_R26FenceInvocationAuthorityV1, invocation_authority)
        exact_page_store = self._page_store
        binding_digest, revision, fingerprint = candidate
        readback = self._receipt_service.lookup_exact(
            binding,
            post_commit_revision=revision,
            post_commit_fingerprint=fingerprint,
            receipt_store=self._receipt_store,
        )
        expected_receipt = _receipt(binding, revision, fingerprint)
        if readback.outcome != "found" or expected_receipt is None:
            return None
        with self._r26_receipt_confirmation_lock:
            if exact_invocation in self._r26_terminal_receipt_confirmation_invocations:
                return None
            if self._r26_pending_receipt_confirmation_v1(
                factory, binding, composition, invocation_authority
            ) != candidate:
                return None
            self._r26_pending_receipt_confirmations.pop(exact_invocation, None)
            confirmation = object.__new__(_ExactReceiptReconciliationConfirmationV1)
            seal = object()
            object.__setattr__(confirmation, "_seal", seal)
            self._r26_receipt_confirmations.add(confirmation)
            self._r26_receipt_confirmation_records[confirmation] = (
                self,
                factory,
                exact_page_store._repository,
                composition,
                invocation_authority,
                binding,
                binding_digest,
                revision,
                fingerprint,
                expected_receipt.canonical_digest,
                confirmation,
                seal,
            )
            self._r26_terminal_receipt_confirmation_invocations.add(exact_invocation)
            return confirmation

    def _begin_r26_receipt_confirmation_consumption_v1(
        self,
        confirmation: object,
        factory: object,
        binding: object,
        composition: object,
        invocation_authority: object,
    ) -> str:
        """Atomically move exactly one registered confirmation to CONSUMING."""

        if type(confirmation) is not _ExactReceiptReconciliationConfirmationV1:
            return "AUTHORITY_REJECTED"
        if (
            type(binding) is not WorkflowApplicationLedgerBindingDTO
            or type(invocation_authority) is not _R26FenceInvocationAuthorityV1
            or type(self._page_store) is not LocalFileDurablePageStore
        ):
            return "AUTHORITY_REJECTED"
        with self._r26_receipt_confirmation_lock:
            if (
                confirmation in self._r26_consuming_receipt_confirmations
                or confirmation in self._r26_consumed_receipt_confirmations
            ):
                return "CONSUMED"
            record = self._r26_receipt_confirmation_records.get(confirmation)
            if record is None:
                return "AUTHORITY_REJECTED"
            if len(record) != 12:
                return "AUTHORITY_REJECTED"
            (
                owner,
                issued_factory,
                repository,
                issued_composition,
                issued_invocation,
                issued_binding,
                binding_digest,
                revision,
                fingerprint,
                receipt_digest,
                issued_confirmation,
                seal,
            ) = record
            if (
                owner is not self
                or issued_factory is not factory
                or repository is not self._page_store._repository
                or issued_composition is not composition
                or composition is not self._r25_localfile_composition
                or issued_invocation is not invocation_authority
                or issued_binding is not binding
                or issued_confirmation is not confirmation
                or getattr(confirmation, "_seal", None) is not seal
                or not isinstance(binding_digest, str)
                or not isinstance(revision, int)
                or isinstance(revision, bool)
                or not _private_fingerprint(fingerprint)
                or not isinstance(receipt_digest, str)
            ):
                return "AUTHORITY_REJECTED"
            if confirmation not in self._r26_receipt_confirmations:
                return "CONSUMED"
            self._r26_receipt_confirmations.remove(confirmation)
            self._r26_consuming_receipt_confirmations.add(confirmation)
            return "CONSUMING"

    def _tombstone_r26_receipt_confirmation_v1(self, confirmation: object) -> None:
        """Irreversibly retire an exact confirmation after entering CONSUMING."""

        if type(confirmation) is not _ExactReceiptReconciliationConfirmationV1:
            return
        with self._r26_receipt_confirmation_lock:
            self._r26_receipt_confirmations.discard(confirmation)
            self._r26_consuming_receipt_confirmations.discard(confirmation)
            self._r26_receipt_confirmation_records.pop(confirmation, None)
            self._r26_consumed_receipt_confirmations.add(confirmation)

    def _finalize_r26_ledger_from_confirmation_v1(
        self,
        confirmation: object,
        factory: object,
        binding: WorkflowApplicationLedgerBindingDTO,
        composition: object,
        invocation_authority: object,
        prepared_observation: object,
    ) -> str:
        """Coordinate the IMP-10 sealed finalizer without giving Ledger a confirmation."""

        state = self._begin_r26_receipt_confirmation_consumption_v1(
            confirmation, factory, binding, composition, invocation_authority
        )
        if state != "CONSUMING":
            return state
        try:
            finalizer = self._r26_ledger_finalizer
            authorization = self._r26_ledger_finalizer_authorization
            if finalizer is not _finalize_r26_ledger_reconciliation_v1 or authorization is None:
                return "RECONCILIATION_RESTART_REQUIRED"
            result = finalizer(authorization, prepared_observation)
            outcome = getattr(result, "outcome", None)
            if outcome not in {
                "APPLIED",
                "CALL_REJECTED",
                "CONFLICT",
                "CORRUPT",
                "RECOVERY_REQUIRED",
                "LEDGER_REPLAY_REQUIRED",
            }:
                return "RECONCILIATION_RESTART_REQUIRED"
            return "AUTHORITY_REJECTED" if outcome == "CALL_REJECTED" else cast(str, outcome)
        except Exception:
            return "RECONCILIATION_RESTART_REQUIRED"
        finally:
            self._tombstone_r26_receipt_confirmation_v1(confirmation)

    def _record_r26_pending_receipt_confirmation_v1(
        self,
        factory: object,
        binding: WorkflowApplicationLedgerBindingDTO,
        composition: object,
        invocation_authority: object,
        projection: object,
    ) -> bool:
        """Retain facts only after the exact projection is irrevocably consumed."""

        if (
            type(self._page_store) is not LocalFileDurablePageStore
            or type(invocation_authority) is not _R26FenceInvocationAuthorityV1
            or invocation_authority._coordinator is not self
            or invocation_authority._binding is not binding
            or invocation_authority._page_store is not self._page_store
            or invocation_authority._fence_context not in self._r26_active_fence_contexts
            or invocation_authority._used is not True
            or type(invocation_authority._fence) is not WindowsPageExecutionFence
            or not invocation_authority._fence._r26_is_held_for(
                binding.project_id, binding.page_id
            )
            or self._r26_proof_factory is not factory
            or composition is not self._r25_localfile_composition
        ):
            return False
        exact_page_store = self._page_store
        facts = _read_consumed_r26_receipt_projection_facts_for_confirmation_v1(
            projection,
            factory,
            binding,
            repository=exact_page_store._repository,
            composition=composition,
            coordinator=self,
            invocation_authority=invocation_authority,
        )
        if facts is None:
            return False
        with self._r26_receipt_confirmation_lock:
            if invocation_authority in self._r26_terminal_receipt_confirmation_invocations:
                return False
            if invocation_authority in self._r26_pending_receipt_confirmations:
                return False
            self._r26_pending_receipt_confirmations[invocation_authority] = (
                factory,
                binding,
                exact_page_store._repository,
                composition,
                facts[0],
                facts[1],
                facts[2],
            )
            return True

    def _r26_pending_receipt_confirmation_v1(
        self,
        factory: object,
        binding: WorkflowApplicationLedgerBindingDTO,
        composition: object,
        invocation_authority: object,
    ) -> tuple[str, int, str] | None:
        """Read this Coordinator's exact pending data without treating it as a capability."""

        if type(invocation_authority) is not _R26FenceInvocationAuthorityV1:
            return None
        if type(self._page_store) is not LocalFileDurablePageStore:
            return None
        exact_page_store = self._page_store
        with self._r26_receipt_confirmation_lock:
            if invocation_authority in self._r26_terminal_receipt_confirmation_invocations:
                return None
            entry = self._r26_pending_receipt_confirmations.get(invocation_authority)
            if entry is None or len(entry) != 7:
                return None
            if (
                entry[0] is not factory
                or entry[1] is not binding
                or entry[2] is not exact_page_store._repository
                or entry[3] is not composition
                or not isinstance(entry[4], str)
                or not isinstance(entry[5], int)
                or isinstance(entry[5], bool)
                or entry[5] < 1
                or not isinstance(entry[6], str)
                or not _private_fingerprint(entry[6])
                or invocation_authority._coordinator is not self
                or invocation_authority._binding is not binding
                or invocation_authority._page_store is not self._page_store
                or invocation_authority._fence_context not in self._r26_active_fence_contexts
                or invocation_authority._used is not True
                or type(invocation_authority._fence) is not WindowsPageExecutionFence
                or not invocation_authority._fence._r26_is_held_for(
                    binding.project_id, binding.page_id
                )
            ):
                return None
            return entry[4], entry[5], entry[6]

    def _discard_r26_pending_receipt_confirmation_v1(self, invocation_authority: object) -> None:
        if type(invocation_authority) is _R26FenceInvocationAuthorityV1:
            with self._r26_receipt_confirmation_lock:
                self._r26_pending_receipt_confirmations.pop(invocation_authority, None)

    def _r30_prepare_and_commit_under_fence(
        self,
        binding: WorkflowApplicationLedgerBindingDTO,
        binding_report: DurableEvidenceWorkflowBindingReport,
        authorization: WorkflowApplicationAuthorizationDTO,
        snapshot: RevisionedProjectSnapshot,
        context: WorkflowContext,
    ) -> ExternalGeneratedApplicationResult:
        prepared = self._ledger_service.prepare(binding_report, authorization, self._ledger_store)
        if prepared.status == "blocked" or prepared.binding != binding:
            return _not_applied(binding, "EXTERNAL_APPLICATION_LEDGER_PREPARE_BLOCKED")
        if prepared.applied is True:
            return self._confirm_applied_replay_under_fence(binding, context)
        if prepared.prepared is not True:
            return _not_applied(binding, "EXTERNAL_APPLICATION_LEDGER_PREPARE_INVALID")
        return self._commit_and_complete(binding, snapshot, context)

    def _apply_prepared(
        self, binding: WorkflowApplicationLedgerBindingDTO
    ) -> ExternalGeneratedApplicationResult:
        fence: PageExecutionFencePort | None = None
        lease: _ExternalApplicationLease | None = None
        try:
            fence = self._fence_factory(binding.project_id, binding.page_id)
            fence.acquire()
            snapshot = self._page_store.load_revisioned(binding.project_id)
            context = self._page_store.context_from_snapshot(snapshot, binding.page_id)
            fence_context = _ExternalApplicationFenceContext._create(binding, snapshot)
            lease, guard_error = self._acquire_guard_lease(
                binding, snapshot, context, fence_context
            )
            if guard_error is not None:
                return _not_applied(binding, guard_error)
            if context.state == PageState.GENERATED:
                return _not_applied(binding, "EXTERNAL_APPLICATION_PREPARED_GENERATED_AMBIGUOUS")
            if context.state != PageState.PROMPT_BUILT:
                return _not_applied(binding, "EXTERNAL_APPLICATION_SOURCE_STATE_MISMATCH")
            return self._commit_and_complete(binding, snapshot, context)
        except PageExecutionFenceError:
            return _not_applied(binding, "EXTERNAL_APPLICATION_PAGE_FENCE_UNAVAILABLE")
        except Exception:
            return _not_applied(binding, "EXTERNAL_APPLICATION_FAILED")
        finally:
            if lease is not None:
                lease.release()
            if fence is not None:
                fence.release()

    def _acquire_guard_lease(
        self,
        binding: WorkflowApplicationLedgerBindingDTO,
        snapshot: RevisionedProjectSnapshot,
        context: WorkflowContext,
        fence_context: _ExternalApplicationFenceContext,
    ) -> tuple[_ExternalApplicationLease | None, str | None]:
        if self._pre_apply_guard is None:
            return None, None
        decision = self._pre_apply_guard.validate(binding, snapshot, context, fence_context)
        if (
            isinstance(decision, _ExternalApplicationGuardDecision)
            and decision.allowed is True
            and decision.lease is not None
        ):
            return decision.lease, None
        code = decision.code if isinstance(decision, _ExternalApplicationGuardDecision) else "INVALID"
        return None, f"EXTERNAL_APPLICATION_PRE_APPLY_GUARD_{code}"

    def _commit_and_complete(
        self,
        binding: WorkflowApplicationLedgerBindingDTO,
        snapshot: RevisionedProjectSnapshot,
        context: WorkflowContext,
    ) -> ExternalGeneratedApplicationResult:
        self._state_machine.validate_transition(PageState.PROMPT_BUILT, PageState.GENERATED)
        event = WorkflowEvent(event_type=EventType.IMAGE_GENERATED, data={"state": PageState.GENERATED.value})
        next_context = context.advance(
            state=PageState.GENERATED,
            events=[event],
            artifact_name=PageState.GENERATED.value,
            payload=_descriptor(binding.output_asset_id),
        )
        project = self._page_store.project_from_context(snapshot, binding.page_id, next_context)
        if not self._record_r30_pre_cas_provenance(binding, snapshot):
            return _not_applied(binding, "EXTERNAL_APPLICATION_R30_PROVENANCE_FAILED")
        committed, r27_intent_invalid = self._authoritative_commit(binding, snapshot, context, project)
        if r27_intent_invalid:
            return _not_applied(binding, "EXTERNAL_APPLICATION_R27_INTENT_INVALID")
        if committed is None:
            return _not_applied(binding, "EXTERNAL_APPLICATION_AUTHORITATIVE_CAS_FAILED")
        if not self._page_store.verify_committed(binding.project_id, binding.page_id, project):
            return _not_applied(binding, "EXTERNAL_APPLICATION_POST_COMMIT_VERIFICATION_FAILED")
        correlation = self._post_commit_correlation(binding, committed)
        if correlation is None:
            return _not_applied(binding, "EXTERNAL_APPLICATION_POST_COMMIT_VERIFICATION_FAILED")
        if not self._materialize_r25_before_continuation(binding, correlation):
            return _not_applied(binding, "EXTERNAL_APPLICATION_R25_MATERIALIZATION_FAILED")
        proof = _authoritative_commit_proof(binding)
        receipt = self._receipt_service.commit(
            binding,
            proof,
            post_commit_revision=correlation[0],
            post_commit_fingerprint=correlation[1],
            receipt_store=self._receipt_store,
        )
        if receipt.committed is not True or receipt.status != "committed":
            return _result(binding, "application_applied_receipt_failed", "EXTERNAL_APPLICATION_RECEIPT_COMMIT_FAILED", False)
        finalized = self._ledger_service.finalize(binding, proof, self._ledger_store)
        if finalized.applied is not True or finalized.status != "applied":
            return _result(binding, "application_applied_ledger_finalize_failed", "EXTERNAL_APPLICATION_LEDGER_FINALIZE_FAILED", False)
        try:
            self._event_bus.publish([event])
        except Exception:
            return _result(binding, "application_applied_event_failed", "APPLICATION_APPLIED_EVENT_FAILED", False)
        return _result(binding, "application_applied_event_published", "EXTERNAL_APPLICATION_APPLIED", True)

    def _authoritative_commit(
        self,
        binding: WorkflowApplicationLedgerBindingDTO,
        snapshot: RevisionedProjectSnapshot,
        context: WorkflowContext,
        project: Project,
    ) -> tuple[object | None, bool]:
        """Retain the existing CAS/R27 publication behavior behind one call."""

        try:
            if self._r27_publication_factory is None:
                return self._page_store.conditional_commit(snapshot, project), False
            if type(self._page_store) is not LocalFileDurablePageStore:
                return None, False
            activate = (
                self._r29_activation_policy._select_first_publication(binding)
                if self._r29_activation_policy is not None
                else False
            )
            intent = self._r27_publication_factory._issue(binding, snapshot, context, project)
            if not _r27_intent_matches_authoritative_facts(
                intent, self._r27_publication_factory, binding, snapshot
            ) or not self._r27_publication_factory._consume_issued(intent):
                return None, True
            if activate:
                return self._page_store._activate_and_conditional_commit_r27(snapshot, project, intent), False
            return self._page_store._conditional_commit_r27(snapshot, project, intent), False
        except Exception:
            return None, False

    def _materialize_r25_before_continuation(
        self, binding: WorkflowApplicationLedgerBindingDTO, correlation: tuple[int, str]
    ) -> bool:
        """Require the private R25 predecessor before Receipt/Ledger continuation."""

        composition = self._r25_localfile_composition
        if composition is None:
            return True
        if type(self._page_store) is not LocalFileDurablePageStore:
            return False
        try:
            return _materialize_normal_r25_v1(
                composition,
                self._page_store._repository,
                binding,
                post_commit_revision=correlation[0],
                post_commit_fingerprint=correlation[1],
            )
        except ValueError:
            return False

    def _record_r30_pre_cas_provenance(
        self, binding: WorkflowApplicationLedgerBindingDTO, snapshot: RevisionedProjectSnapshot
    ) -> bool:
        """Persist the normal-path predecessor while the canonical fence is held."""

        composition = self._r25_localfile_composition
        if composition is None:
            return True
        if type(self._page_store) is not LocalFileDurablePageStore:
            return False
        try:
            return _record_normal_r30_pre_cas_provenance_v1(
                composition,
                self._page_store._repository,
                binding,
                expected_pre_cas_revision=snapshot.revision,
                expected_pre_cas_fingerprint=snapshot.fingerprint,
            )
        except ValueError:
            return False

    def _post_commit_correlation(
        self,
        binding: WorkflowApplicationLedgerBindingDTO,
        committed: object,
    ) -> tuple[int, str] | None:
        """Read the exact verified aggregate revision that the Receipt correlates."""

        revision = getattr(committed, "revision", None)
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
            return None
        snapshot = self._page_store.load_revisioned(binding.project_id)
        if getattr(snapshot, "revision", None) != revision:
            return None
        fingerprint = getattr(snapshot, "fingerprint", None)
        if not _private_fingerprint(fingerprint):
            return None
        context = self._page_store.context_from_snapshot(snapshot, binding.page_id)
        if (
            context.state != PageState.GENERATED
            or context.artifacts.get(PageState.GENERATED.value) != _descriptor(binding.output_asset_id)
        ):
            return None
        return revision, cast(str, fingerprint)

    def _confirm_applied_replay(
        self, binding: WorkflowApplicationLedgerBindingDTO
    ) -> ExternalGeneratedApplicationResult:
        fence: PageExecutionFencePort | None = None
        try:
            fence = self._fence_factory(binding.project_id, binding.page_id)
            fence.acquire()
            snapshot = self._page_store.load_revisioned(binding.project_id)
            context = self._page_store.context_from_snapshot(snapshot, binding.page_id)
            return self._confirm_applied_replay_under_fence(binding, context)
        except PageExecutionFenceError:
            return _not_applied(binding, "EXTERNAL_APPLICATION_PAGE_FENCE_UNAVAILABLE")
        except Exception:
            return _not_applied(binding, "EXTERNAL_APPLICATION_APPLIED_REPLAY_FAILED")
        finally:
            if fence is not None:
                fence.release()

    def _confirm_applied_replay_under_fence(
        self, binding: WorkflowApplicationLedgerBindingDTO, context: WorkflowContext
    ) -> ExternalGeneratedApplicationResult:
        """Confirm an already-applied binding while the caller holds the page fence."""

        if context.state == PageState.PROMPT_BUILT:
            return _not_applied(binding, "EXTERNAL_APPLICATION_APPLIED_PROMPT_BUILT_CONFLICT")
        if context.state != PageState.GENERATED or context.artifacts.get(PageState.GENERATED.value) != _descriptor(
            binding.output_asset_id
        ):
            return _not_applied(binding, "EXTERNAL_APPLICATION_APPLIED_REPLAY_CONFLICT")
        applied = self._ledger_service.lookup_applied(
            binding.project_id, binding.page_id, binding.output_asset_id, self._ledger_store
        )
        if (
            applied.applied is not True
            or applied.binding != binding
            or applied.status != "applied"
        ):
            return _not_applied(binding, "EXTERNAL_APPLICATION_APPLIED_REPLAY_PROOF_INVALID")
        composition = self._r25_localfile_composition
        if composition is not None:
            if type(self._page_store) is not LocalFileDurablePageStore:
                return _not_applied(binding, "EXTERNAL_APPLICATION_APPLIED_REPLAY_PROOF_INVALID")
            try:
                snapshot = self._page_store.load_revisioned(binding.project_id)
                exact = _require_exact_localfile_r25_composition_v1(
                    composition, self._page_store._repository
                )
                record = exact._r25_store._replay_post_cas_attestation_exact_v1(
                    _r27_application_binding_identity(binding)
                )
                receipt = self._receipt_service.lookup_exact(
                    binding,
                    post_commit_revision=snapshot.revision,
                    post_commit_fingerprint=snapshot.fingerprint,
                    receipt_store=self._receipt_store,
                )
            except (ValueError, LocalFileDurabilityError):
                return _not_applied(binding, "EXTERNAL_APPLICATION_APPLIED_REPLAY_PROOF_INVALID")
            if (
                record is None
                or record.values[21] != snapshot.revision
                or record.values[22] != snapshot.fingerprint
                or receipt.outcome != "found"
            ):
                return _not_applied(binding, "EXTERNAL_APPLICATION_APPLIED_REPLAY_PROOF_INVALID")
        return _result(
            binding,
            "application_replay_confirmed",
            "EXTERNAL_APPLICATION_APPLIED_REPLAY_CONFIRMED",
            False,
        )


@dataclass(frozen=True, slots=True)
class LocalFileExternalGenerationComposition:
    """Private shared LocalFile integration objects for one trusted runtime."""

    ledger_service: WorkflowApplicationLedgerService
    ledger_store: WorkflowApplicationLedgerStorePort
    receipt_service: DurableApplicationCommitReceiptService
    receipt_store: DurableApplicationCommitReceiptStorePort
    quality_gate: LocalFileLogicalOutputAssetQualityGate
    external_application: LocalFileExternalGeneratedApplicationCoordinator


def build_localfile_external_generation_composition(
    repository: LocalFileRepository,
    state_machine: StateMachine,
    event_bus: EventBus,
) -> LocalFileExternalGenerationComposition:
    """Compose the private Ledger sidecar from the repository durability owner only."""

    return _build_localfile_external_generation_composition_v1(
        repository,
        state_machine,
        event_bus,
        r25_composition=_construct_localfile_r25_composition_v1(repository),
    )


def _build_localfile_external_generation_composition_v1(
    repository: LocalFileRepository,
    state_machine: StateMachine,
    event_bus: EventBus,
    *,
    r25_composition: object | None,
) -> LocalFileExternalGenerationComposition:
    """Assemble shared private dependencies without selecting R25 resources."""

    ledger_service, ledger_store, quality_gate = _ledger_quality_gate(repository)
    receipt_service = DurableApplicationCommitReceiptService()
    receipt_store = LocalDurableApplicationCommitReceiptStore(
        repository._workflow_application_ledger_owner_root()
    )
    pair = object()
    page_store = LocalFileDurablePageStore(repository, _r27_pair=pair)
    coordinator = LocalFileExternalGeneratedApplicationCoordinator(
        state_machine,
        event_bus,
        ledger_service,
        ledger_store,
        receipt_service,
        receipt_store,
        page_store,
        _r27_publication_factory=_R27PublicationIntentFactory(pair, _issuer=_R27_FACTORY_ISSUER),
    )
    coordinator._r29_activation_policy = _R27ProjectActivationPolicy(repository)
    # Only the real canonical builder supplies the R25/R30 private tuple.
    coordinator._r25_localfile_composition = r25_composition
    return LocalFileExternalGenerationComposition(
        ledger_service=ledger_service,
        ledger_store=ledger_store,
        receipt_service=receipt_service,
        receipt_store=receipt_store,
        quality_gate=quality_gate,
        external_application=coordinator,
    )


def _build_private_real_delivery_canonical_external_generation_composition_from_owned_repository_v1(
    repository: object,
    state_machine: object,
    event_bus: object,
) -> LocalFileExternalGenerationComposition:
    """Private R26 bootstrap inlet over one already-owned exact LocalFile tuple.

    It introduces no selector and is intentionally not used by the public or
    fake-only builders.  The workflow-private caller has already established
    object identity; this helper merely preserves it through the canonical
    composition construction.
    """

    if type(repository) is not LocalFileRepository or type(state_machine) is not StateMachine:
        raise ValueError("AUTHORITY_REJECTED")
    if not callable(getattr(event_bus, "publish", None)) or not callable(
        getattr(event_bus, "subscribe", None)
    ):
        raise ValueError("AUTHORITY_REJECTED")
    exact_repository = repository
    composition = _build_localfile_external_generation_composition_v1(
        exact_repository,
        state_machine,
        cast(EventBus, event_bus),
        r25_composition=_construct_localfile_r25_composition_v1(exact_repository),
    )
    coordinator = composition.external_application
    if (
        not isinstance(coordinator._page_store, LocalFileDurablePageStore)
        or coordinator._page_store._repository is not exact_repository
        or coordinator._r25_localfile_composition is None
    ):
        raise ValueError("AUTHORITY_REJECTED")
    finalizer_authorization = _issue_r26_ledger_finalizer_authorization_v1(
        composition.ledger_service,
        composition.ledger_store,
        exact_repository,
        coordinator,
        composition,
        _issuer=_R26_FINALIZER_ISSUER,
    )
    coordinator._r26_ledger_finalizer = _finalize_r26_ledger_reconciliation_v1
    coordinator._r26_ledger_finalizer_authorization = finalizer_authorization
    return composition


def _build_localfile_r27_publication_test_composition(
    repository: LocalFileRepository,
    state_machine: StateMachine,
    event_bus: EventBus,
) -> LocalFileExternalGenerationComposition:
    """Build the sole private R28 test composition; normal composition stays legacy."""

    ledger_service, ledger_store, quality_gate = _ledger_quality_gate(repository)
    receipt_service = DurableApplicationCommitReceiptService()
    receipt_store = LocalDurableApplicationCommitReceiptStore(
        repository._workflow_application_ledger_owner_root()
    )
    pair = object()
    page_store = LocalFileDurablePageStore(repository, _r27_pair=pair)
    return LocalFileExternalGenerationComposition(
        ledger_service=ledger_service,
        ledger_store=ledger_store,
        receipt_service=receipt_service,
        receipt_store=receipt_store,
        quality_gate=quality_gate,
        external_application=LocalFileExternalGeneratedApplicationCoordinator(
            state_machine,
            event_bus,
            ledger_service,
            ledger_store,
            receipt_service,
            receipt_store,
            page_store,
            _r27_publication_factory=_R27PublicationIntentFactory(
                pair, _issuer=_R27_FACTORY_ISSUER
            ),
        ),
    )
def build_localfile_quality_ledger_gate(
    repository: LocalFileRepository,
) -> LocalFileLogicalOutputAssetQualityGate:
    """Build the same private Ledger-backed gate for a LocalFile host composition."""

    return _ledger_quality_gate(repository)[2]


def _ledger_quality_gate(
    repository: LocalFileRepository,
) -> tuple[
    WorkflowApplicationLedgerService,
    WorkflowApplicationLedgerStorePort,
    LocalFileLogicalOutputAssetQualityGate,
]:
    ledger_service = WorkflowApplicationLedgerService()
    ledger_store = LocalWorkflowApplicationLedgerStore(repository._workflow_application_ledger_owner_root())
    return ledger_service, ledger_store, LocalFileLogicalOutputAssetQualityGate(
        ledger_service, ledger_store
    )


def _logical_output_values(context: WorkflowContext) -> tuple[str, str, str] | None:
    if context.state != PageState.GENERATED:
        return None
    image = context.artifacts.get(PageState.GENERATED.value)
    if not isinstance(image, Mapping) or set(image) != {"artifact_kind", "output_asset_id"}:
        return None
    output_asset_id = image.get("output_asset_id")
    project_id = context.page.get("project_id")
    page_id = context.page.get("page_id")
    if (
        image.get("artifact_kind") != "logical_output_asset"
        or not _logical_reference(project_id)
        or not _logical_reference(page_id)
        or not _logical_reference(output_asset_id)
    ):
        return None
    return cast(tuple[str, str, str], (project_id, page_id, output_asset_id))


def _binding_matches(
    binding: WorkflowApplicationLedgerBindingDTO,
    project_id: str,
    page_id: str,
    output_asset_id: str,
) -> bool:
    return (
        binding.project_id == project_id
        and binding.page_id == page_id
        and binding.output_asset_id == output_asset_id
        and binding.source_state == "PromptBuilt"
        and binding.target_state == "Generated"
    )


def _descriptor(output_asset_id: str) -> dict[str, str]:
    return {"artifact_kind": "logical_output_asset", "output_asset_id": output_asset_id}


def _result_identity(
    report: DurableEvidenceWorkflowBindingReport,
) -> tuple[str, str]:
    return report.project_id, report.page_id


def _result(
    binding: WorkflowApplicationLedgerBindingDTO,
    status: ExternalApplicationStatus,
    code: str,
    event_published: bool,
) -> ExternalGeneratedApplicationResult:
    return ExternalGeneratedApplicationResult(
        project_id=binding.project_id,
        page_id=binding.page_id,
        status=status,
        code=code,
        event_published=event_published,
    )


def _not_applied(
    identity: WorkflowApplicationLedgerBindingDTO | tuple[str, str], code: str
) -> ExternalGeneratedApplicationResult:
    project_id, page_id = (
        (identity.project_id, identity.page_id)
        if isinstance(identity, WorkflowApplicationLedgerBindingDTO)
        else identity
    )
    return ExternalGeneratedApplicationResult(
        project_id=project_id,
        page_id=page_id,
        status="application_not_applied",
        code=code,
        event_published=False,
    )


def _logical_reference(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.strip()
        and not value.startswith(("/", "\\"))
        and "://" not in value
        and "@" not in value
        and not any(character.isspace() for character in value)
    )


def _private_fingerprint(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )
