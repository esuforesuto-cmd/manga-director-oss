"""Private sequential orchestration for panel-aware Page generation."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import partial
from typing import Literal, Protocol, runtime_checkable

from manga_director.production.next_generation_deterministic_composite_asset_owner import (
    DeterministicCompositeAssetOwner,
)
from manga_director.production.next_generation_deterministic_page_compositor import (
    CompositeInputError,
    compose_page,
)
from manga_director.production.next_generation_page_composition import (
    AcceptedPanelSource,
    LocalPageCompositionAuthority,
    PageCompositeAsset,
    PageCompositionAttempt,
    PageCompositionAuthorityResult,
    PageCompositionEvidence,
    PageCompositionRequest,
)
from manga_director.production.next_generation_page_composition_application_ledger import (
    LocalPageCompositionApplicationLedger,
    PageCompositionApplicationBinding,
)
from manga_director.production.next_generation_page_generation_mode_claim import (
    PageGenerationModeClaim,
)
from manga_director.production.next_generation_page_generation_plan import (
    PageGenerationPlan,
)
from manga_director.production.next_generation_page_output_proof import (
    DeterministicCompositionPageOutputProof,
    PageOutputApplicationAdmission,
    composition_evidence_sha256,
)
from manga_director.production.next_generation_panel_execution_attempt import (
    PanelAttemptReservation,
    PanelGenerationRequest,
)
from manga_director.production.next_generation_panel_generation_evidence import (
    LocalPanelGenerationAuthority,
    PanelAsset,
    PanelGenerationAuthorityResult,
    PanelGenerationEvidence,
)
from manga_director.workflow.localfile_page_generation_mode_admission import (
    LocalFilePageGenerationModeAdmission,
)
from manga_director.workflow.page_execution_fence import PageExecutionFencePort


@dataclass(frozen=True, slots=True)
class PanelProviderExecution:
    outcome: Literal["succeeded", "declared_failure", "recovery_required"]
    asset: PanelAsset | None = field(default=None, repr=False)
    evidence: PanelGenerationEvidence | None = field(default=None, repr=False)
    image_bytes: bytes | None = field(default=None, repr=False)


class PanelProviderExecutionPort(Protocol):
    def invoke(
        self, request: PanelGenerationRequest, reservation: PanelAttemptReservation
    ) -> PanelProviderExecution: ...


@runtime_checkable
class _PreparatoryPanelProviderExecutionPort(PanelProviderExecutionPort, Protocol):
    """Private capability for read-only preparation before durable provider-start."""

    def prepare(
        self, request: PanelGenerationRequest, reservation: PanelAttemptReservation
    ) -> Callable[[], PanelProviderExecution] | None: ...


class AcceptedPanelAssetReaderPort(Protocol):
    def read(self, asset: PanelAsset) -> bytes | None: ...


class ExistingGenerateCommandPort(Protocol):
    """The existing WorkflowEngine/StateMachine-owned ``generate`` inlet."""

    def generate(
        self,
        binding: PageCompositionApplicationBinding,
        proof: DeterministicCompositionPageOutputProof,
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class PanelGenerationUnit:
    request: PanelGenerationRequest
    reservation: PanelAttemptReservation


@dataclass(frozen=True, slots=True)
class PanelAwarePageGenerationOperation:
    plan: PageGenerationPlan
    mode_claim: PageGenerationModeClaim
    panel_units: tuple[PanelGenerationUnit, ...]
    page_revision: str
    composition_attempt_id: str
    composition_authorization_reference: str
    composition_provenance_reference: str
    composition_evidence_id: str
    composite_asset_id: str
    application_id: str


@dataclass(frozen=True, slots=True)
class PanelAwarePageGenerationResult:
    status: Literal["generated", "partial", "blocked", "recovery_required"]
    code: str
    provider_calls: int
    accepted_panel_ids: tuple[str, ...] = ()
    proof: DeterministicCompositionPageOutputProof | None = field(
        default=None, repr=False
    )

    @property
    def generated(self) -> bool:
        return self.status == "generated"


class LocalFilePanelAwarePageGeneration:
    """Execute only the exact admitted Panels and one deterministic composition."""

    def __init__(
        self,
        *,
        mode_admission: LocalFilePageGenerationModeAdmission,
        panel_authority: LocalPanelGenerationAuthority,
        provider: PanelProviderExecutionPort,
        panel_reader: AcceptedPanelAssetReaderPort,
        composition_authority: LocalPageCompositionAuthority,
        composite_owner: DeterministicCompositeAssetOwner,
        application_ledger: LocalPageCompositionApplicationLedger,
        generate_command: ExistingGenerateCommandPort,
    ) -> None:
        self._mode_admission = mode_admission
        self._panel_authority = panel_authority
        self._provider = provider
        self._panel_reader = panel_reader
        self._composition_authority = composition_authority
        self._composite_owner = composite_owner
        self._application_ledger = application_ledger
        self._generate_command = generate_command

    def execute(  # noqa: C901 - ordered durable fail-closed gates stay visible
        self,
        operation: PanelAwarePageGenerationOperation,
        *,
        admission_fence: PageExecutionFencePort,
    ) -> PanelAwarePageGenerationResult:
        if not _operation_matches(operation):
            return _result("blocked", "operation_binding_mismatch", 0, ())
        replay_admission, replay = (
            self._mode_admission.run_generated_replay_admitted(
                operation.mode_claim,
                admission_fence,
                operation.composite_asset_id,
                lambda: self._replay_generated_operation(
                    operation, admission_fence
                ),
            )
        )
        if replay_admission.admitted:
            if replay is not None:
                return replay
            return _result(
                "recovery_required",
                "generated_replay_verification_unavailable",
                0,
                (),
            )
        if replay_admission.code != "generated_replay_not_applicable":
            return _result("blocked", replay_admission.code, 0, ())
        admission = self._mode_admission.admit(
            operation.mode_claim, admission_fence
        )
        if not admission.admitted:
            return _result("blocked", admission.code, 0, ())

        accepted: list[tuple[PanelAsset, PanelGenerationEvidence, bytes]] = []
        provider_calls = 0
        for unit in operation.panel_units:
            recovered = self._accepted_existing(unit)
            if recovered is not None:
                accepted.append(recovered)
                continue
            lookup = self._panel_authority.lookup_attempt(
                unit.reservation.attempt_id
            )
            reuse_reserved = False
            if lookup.outcome == "confirmed":
                record = lookup.record
                reuse_reserved = bool(
                    isinstance(self._provider, _PreparatoryPanelProviderExecutionPort)
                    and record is not None
                    and record.reservation == unit.reservation
                    and record.state == "RESERVED"
                    and not record.provider_start_consumed
                )
                if not reuse_reserved:
                    return _result(
                        "recovery_required",
                        "panel_attempt_requires_recovery",
                        provider_calls,
                        tuple(item[0].panel_id for item in accepted),
                    )
            elif lookup.outcome not in {"missing"}:
                return _result(
                    "blocked",
                    "panel_attempt_unavailable",
                    provider_calls,
                    tuple(item[0].panel_id for item in accepted),
                )
            if not reuse_reserved:
                reserved = self._panel_authority.reserve(unit.reservation)
                if reserved.outcome not in {"created", "confirmed"}:
                    return _result(
                        "blocked",
                        "panel_attempt_not_reserved",
                        provider_calls,
                        tuple(item[0].panel_id for item in accepted),
                    )
                confirmed = self._panel_authority.lookup_attempt(
                    unit.reservation.attempt_id
                )
                if (
                    confirmed.outcome != "confirmed"
                    or confirmed.record is None
                    or confirmed.record.reservation != unit.reservation
                    or confirmed.record.state != "RESERVED"
                    or confirmed.record.provider_start_consumed
                ):
                    return _result(
                        "recovery_required",
                        "panel_reservation_not_authoritative",
                        provider_calls,
                        tuple(item[0].panel_id for item in accepted),
                    )

            preparatory_provider = (
                self._provider
                if isinstance(self._provider, _PreparatoryPanelProviderExecutionPort)
                else None
            )
            prepared: Callable[[], PanelProviderExecution] | None = None
            if preparatory_provider is not None:
                try:
                    prepared = preparatory_provider.prepare(unit.request, unit.reservation)
                except Exception:
                    prepared = None
                if prepared is None:
                    return _result(
                        "blocked",
                        "panel_provider_preparation_failed",
                        provider_calls,
                        tuple(item[0].panel_id for item in accepted),
                    )
            start_admission, started = self._mode_admission.run_provider_start_admitted(
                operation.mode_claim,
                admission_fence,
                partial(self._panel_authority.start_provider, unit.reservation),
            )
            if not start_admission.admitted:
                return _result(
                    "blocked",
                    start_admission.code,
                    provider_calls,
                    tuple(item[0].panel_id for item in accepted),
                )
            if started is None or started.outcome != "updated":
                return _result(
                    "recovery_required",
                    "provider_start_not_exclusive",
                    provider_calls,
                    tuple(item[0].panel_id for item in accepted),
                )
            provider_calls += 1
            try:
                execution = (
                    prepared()
                    if preparatory_provider is not None and prepared is not None
                    else self._provider.invoke(unit.request, unit.reservation)
                )
            except Exception:
                recovery_recorded = _require_panel_recovery_durable(
                    self._panel_authority, unit.reservation
                )
                return _result(
                    "recovery_required",
                    (
                        "provider_outcome_ambiguous"
                        if recovery_recorded
                        else "panel_recovery_not_recorded"
                    ),
                    provider_calls,
                    tuple(item[0].panel_id for item in accepted),
                )
            if execution.outcome == "declared_failure":
                try:
                    declared = self._panel_authority.declare_failure(unit.reservation)
                except Exception:
                    declared = PanelGenerationAuthorityResult(
                        unit.reservation.attempt_id, "failed"
                    )
                if not _panel_terminal_is_durable(
                    self._panel_authority,
                    unit.reservation,
                    declared,
                    "DECLARED_FAILURE",
                ):
                    return _result(
                        "recovery_required",
                        "panel_declared_failure_not_recorded",
                        provider_calls,
                        tuple(item[0].panel_id for item in accepted),
                    )
                return _result(
                    "partial",
                    "panel_declared_failure",
                    provider_calls,
                    tuple(item[0].panel_id for item in accepted),
                )
            if execution.outcome != "succeeded":
                recovery_recorded = _require_panel_recovery_durable(
                    self._panel_authority, unit.reservation
                )
                return _result(
                    "recovery_required",
                    (
                        "provider_outcome_ambiguous"
                        if recovery_recorded
                        else "panel_recovery_not_recorded"
                    ),
                    provider_calls,
                    tuple(item[0].panel_id for item in accepted),
                )
            completed = self._panel_authority.record_provider_completed(
                unit.reservation
            )
            if completed.outcome != "updated" or not _successful_panel_matches(
                unit, execution
            ):
                recovery_recorded = _require_panel_recovery_durable(
                    self._panel_authority, unit.reservation
                )
                return _result(
                    "recovery_required",
                    (
                        "panel_output_mismatch"
                        if recovery_recorded
                        else "panel_recovery_not_recorded"
                    ),
                    provider_calls,
                    tuple(item[0].panel_id for item in accepted),
                )
            asset = execution.asset
            evidence = execution.evidence
            image_bytes = execution.image_bytes
            assert asset is not None and evidence is not None and image_bytes is not None
            registered = self._panel_authority.record_asset_registered(
                unit.reservation, asset.asset_id
            )
            if registered.outcome != "updated":
                return _result(
                    "recovery_required",
                    "panel_asset_not_recorded",
                    provider_calls,
                    tuple(item[0].panel_id for item in accepted),
                )
            committed = self._panel_authority.commit_evidence(
                unit.reservation, evidence
            )
            if committed.outcome != "updated":
                recovery_recorded = _require_panel_recovery_durable(
                    self._panel_authority, unit.reservation
                )
                return _result(
                    "recovery_required",
                    (
                        "panel_evidence_not_committed"
                        if recovery_recorded
                        else "panel_recovery_not_recorded"
                    ),
                    provider_calls,
                    tuple(item[0].panel_id for item in accepted),
                )
            accepted_result = self._panel_authority.accept_panel(unit.reservation)
            if accepted_result.outcome != "updated":
                return _result(
                    "recovery_required",
                    "panel_not_accepted",
                    provider_calls,
                    tuple(item[0].panel_id for item in accepted),
                )
            accepted.append((asset, evidence, image_bytes))

        if len(accepted) != operation.plan.panel_count:
            return _result(
                "partial",
                "panel_set_incomplete",
                provider_calls,
                tuple(item[0].panel_id for item in accepted),
            )
        sources = _accepted_sources(operation.plan, accepted)
        try:
            request = PageCompositionRequest(
                composition_attempt_id=operation.composition_attempt_id,
                plan_id=operation.plan.plan_id,
                plan_fingerprint=operation.plan.plan_fingerprint or "",
                project_id=operation.plan.project_id,
                page_id=operation.plan.page_id,
                explicit_authorization_reference=(
                    operation.composition_authorization_reference
                ),
                composition_provenance_reference=(
                    operation.composition_provenance_reference
                ),
                margins=operation.plan.margins,
                gutter_px=operation.plan.gutter_px,
                panel_count=operation.plan.panel_count,
                sources=sources,
            )
        except ValueError:
            return _result(
                "blocked",
                "composition_set_invalid",
                provider_calls,
                tuple(item[0].panel_id for item in accepted),
            )
        existing_composition = self._composition_authority.lookup(
            request.composition_attempt_id
        )
        if existing_composition.outcome == "confirmed":
            return self._resume_existing_composition(
                operation,
                request,
                existing_composition,
                provider_calls,
                tuple(item[0].panel_id for item in accepted),
                admission_fence,
            )
        if existing_composition.outcome != "missing":
            return _result(
                "blocked",
                "composition_authority_unavailable",
                provider_calls,
                tuple(item[0].panel_id for item in accepted),
            )
        reservation = self._composition_authority.reserve(request)
        if reservation.outcome != "created":
            return _result(
                "blocked",
                "composition_not_reserved",
                provider_calls,
                tuple(item[0].panel_id for item in accepted),
            )
        try:
            composite_bytes = compose_page(
                request, tuple(item[2] for item in accepted)
            )
        except (CompositeInputError, ValueError):
            if not self._commit_failed_composition(operation, request, "failed"):
                return _result(
                    "recovery_required",
                    "composition_failure_not_recorded",
                    provider_calls,
                    tuple(item[0].panel_id for item in accepted),
                )
            return _result(
                "partial",
                "composition_failed",
                provider_calls,
                tuple(item[0].panel_id for item in accepted),
            )
        except Exception:
            recorded = self._commit_failed_composition(
                operation, request, "recovery_required"
            )
            return _result(
                "recovery_required",
                (
                    "composition_outcome_ambiguous"
                    if recorded
                    else "composition_recovery_not_recorded"
                ),
                provider_calls,
                tuple(item[0].panel_id for item in accepted),
            )
        try:
            composite = PageCompositeAsset(
                composition_attempt_id=request.composition_attempt_id,
                request_fingerprint=request.request_fingerprint or "",
                composition_provenance_reference=(
                    request.composition_provenance_reference
                ),
                ordered_sources=request.sources,
                asset_id=operation.composite_asset_id,
                content_sha256=hashlib.sha256(composite_bytes).hexdigest(),
            )
        except Exception:
            recorded = self._commit_failed_composition(
                operation, request, "recovery_required"
            )
            return _result(
                "recovery_required",
                (
                    "composite_binding_invalid"
                    if recorded
                    else "composition_recovery_not_recorded"
                ),
                provider_calls,
                tuple(item[0].panel_id for item in accepted),
            )
        try:
            composite_registered = self._composite_owner.register(
                composite, composite_bytes
            )
        except Exception:
            composite_registered = None
        if composite_registered is None:
            recorded = self._commit_failed_composition(
                operation, request, "recovery_required"
            )
            return _result(
                "recovery_required",
                (
                    "composite_registration_ambiguous"
                    if recorded
                    else "composition_recovery_not_recorded"
                ),
                provider_calls,
                tuple(item[0].panel_id for item in accepted),
            )
        if composite_registered.outcome not in {"registered", "confirmed"}:
            recorded = self._commit_failed_composition(
                operation, request, "recovery_required"
            )
            return _result(
                "recovery_required",
                (
                    "composite_not_registered"
                    if recorded
                    else "composition_recovery_not_recorded"
                ),
                provider_calls,
                tuple(item[0].panel_id for item in accepted),
            )
        try:
            composition_evidence = PageCompositionEvidence(
                evidence_id=operation.composition_evidence_id,
                composition_attempt_id=request.composition_attempt_id,
                plan_id=request.plan_id,
                plan_fingerprint=request.plan_fingerprint,
                project_id=request.project_id,
                page_id=request.page_id,
                request_fingerprint=request.request_fingerprint or "",
                composition_provenance_reference=(
                    request.composition_provenance_reference
                ),
                ordered_sources=request.sources,
                output_asset_id=composite.asset_id,
                output_sha256=composite.content_sha256,
                outcome="completed",
            )
            evidence_result = self._composition_authority.commit_evidence(
                composition_evidence
            )
        except Exception:
            return _result(
                "recovery_required",
                "composition_evidence_not_committed",
                provider_calls,
                tuple(item[0].panel_id for item in accepted),
            )
        if evidence_result.outcome not in {"updated", "confirmed"}:
            return _result(
                "recovery_required",
                "composition_evidence_not_committed",
                provider_calls,
                tuple(item[0].panel_id for item in accepted),
            )
        return self._apply_completed_composition(
            operation,
            request,
            composition_evidence,
            composite,
            provider_calls,
            tuple(item[0].panel_id for item in accepted),
            admission_fence,
        )

    def _resume_existing_composition(
        self,
        operation: PanelAwarePageGenerationOperation,
        request: PageCompositionRequest,
        existing: PageCompositionAuthorityResult,
        provider_calls: int,
        accepted_panel_ids: tuple[str, ...],
        admission_fence: PageExecutionFencePort,
        *,
        applied_only: bool = False,
    ) -> PanelAwarePageGenerationResult:
        attempt = existing.attempt
        evidence = existing.evidence
        if attempt is None or not _composition_attempt_matches_request(attempt, request):
            return _result(
                "blocked",
                "composition_binding_mismatch",
                provider_calls,
                accepted_panel_ids,
            )
        if attempt.outcome == "reserved" and evidence is None:
            return _result(
                "recovery_required",
                "composition_requires_recovery",
                provider_calls,
                accepted_panel_ids,
            )
        if evidence is None or not _composition_evidence_matches_request(
            operation, request, evidence, attempt.outcome
        ):
            return _result(
                "blocked",
                "composition_evidence_mismatch",
                provider_calls,
                accepted_panel_ids,
            )
        if attempt.outcome == "failed":
            return _result(
                "partial",
                "composition_failed",
                provider_calls,
                accepted_panel_ids,
            )
        if attempt.outcome == "recovery_required":
            return _result(
                "recovery_required",
                "composition_requires_recovery",
                provider_calls,
                accepted_panel_ids,
            )
        if attempt.outcome != "completed":
            return _result(
                "blocked",
                "composition_outcome_invalid",
                provider_calls,
                accepted_panel_ids,
            )
        try:
            read = self._composite_owner.read_verified(operation.composite_asset_id)
        except Exception:
            read = None
        if (
            read is None
            or read.outcome != "found"
            or read.asset is None
            or read.image_bytes is None
            or evidence.output_asset_id != read.asset.asset_id
            or evidence.output_sha256 != read.asset.content_sha256
        ):
            return _result(
                "recovery_required",
                "composite_recovery_unavailable",
                provider_calls,
                accepted_panel_ids,
            )
        return self._apply_completed_composition(
            operation,
            request,
            evidence,
            read.asset,
            provider_calls,
            accepted_panel_ids,
            admission_fence,
            applied_only=applied_only,
        )

    def _apply_completed_composition(
        self,
        operation: PanelAwarePageGenerationOperation,
        request: PageCompositionRequest,
        evidence: PageCompositionEvidence,
        composite: PageCompositeAsset,
        provider_calls: int,
        accepted_panel_ids: tuple[str, ...],
        admission_fence: PageExecutionFencePort,
        *,
        applied_only: bool = False,
    ) -> PanelAwarePageGenerationResult:
        binding = PageCompositionApplicationBinding(
            application_id=operation.application_id,
            project_id=request.project_id,
            page_id=request.page_id,
            page_revision=operation.page_revision,
            plan_id=request.plan_id,
            plan_fingerprint=request.plan_fingerprint,
            composition_attempt_id=request.composition_attempt_id,
            composition_provenance_reference=(
                request.composition_provenance_reference
            ),
            request_fingerprint=request.request_fingerprint or "",
            evidence_id=evidence.evidence_id,
            evidence_sha256=composition_evidence_sha256(evidence),
            composite_asset_id=composite.asset_id,
            composite_sha256=composite.content_sha256,
        )
        proof = DeterministicCompositionPageOutputProof(
            project_id=binding.project_id,
            page_id=binding.page_id,
            target_page_reference=f"page.{binding.project_id}.{binding.page_id}",
            attempt_id=binding.composition_attempt_id,
            provenance_reference=binding.composition_provenance_reference,
            asset_id=binding.composite_asset_id,
            content_sha256=binding.composite_sha256,
            plan_id=binding.plan_id,
            plan_fingerprint=binding.plan_fingerprint,
            request_fingerprint=binding.request_fingerprint,
            evidence_id=binding.evidence_id,
            evidence_sha256=binding.evidence_sha256,
            ordered_sources=composite.ordered_sources,
        )
        admission = PageOutputApplicationAdmission().admit(
            proof,
            composition_binding=binding,
            composition_evidence=evidence,
            composite_asset=composite,
        )
        if not admission.allowed:
            return _result(
                "blocked",
                admission.code,
                provider_calls,
                accepted_panel_ids,
            )
        ledger = self._application_ledger.lookup_exact(binding)
        if ledger.outcome == "confirmed" and ledger.lifecycle == "applied":
            return PanelAwarePageGenerationResult(
                "generated",
                "generated",
                provider_calls,
                accepted_panel_ids,
                proof,
            )
        if ledger.outcome == "confirmed":
            return _result(
                "recovery_required",
                "application_outcome_requires_recovery",
                provider_calls,
                accepted_panel_ids,
            )
        if applied_only:
            return _result(
                "blocked",
                "generated_replay_application_unavailable",
                provider_calls,
                accepted_panel_ids,
            )
        if ledger.outcome != "missing":
            return _result(
                "blocked",
                "application_ledger_unavailable",
                provider_calls,
                accepted_panel_ids,
            )
        prepared = self._application_ledger.prepare(binding)
        if prepared.outcome == "confirmed" and prepared.lifecycle == "applied":
            return PanelAwarePageGenerationResult(
                "generated",
                "generated",
                provider_calls,
                accepted_panel_ids,
                proof,
            )
        if prepared.outcome == "confirmed":
            return _result(
                "recovery_required",
                "application_outcome_requires_recovery",
                provider_calls,
                accepted_panel_ids,
            )
        if prepared.outcome != "prepared":
            return _result(
                "blocked",
                "application_not_prepared",
                provider_calls,
                accepted_panel_ids,
            )
        final_admission, applied = self._mode_admission.run_admitted(
            operation.mode_claim,
            admission_fence,
            lambda: self._generate_command.generate(binding, proof),
        )
        if not final_admission.admitted:
            return _result(
                "blocked",
                final_admission.code,
                provider_calls,
                accepted_panel_ids,
            )
        if not applied:
            return _result(
                "recovery_required",
                "generate_outcome_ambiguous",
                provider_calls,
                accepted_panel_ids,
            )
        finalized = self._application_ledger.mark_applied(binding)
        if finalized.outcome not in {"applied", "confirmed"}:
            return _result(
                "recovery_required",
                "application_ledger_not_finalized",
                provider_calls,
                accepted_panel_ids,
            )
        return PanelAwarePageGenerationResult(
            "generated",
            "generated",
            provider_calls,
            accepted_panel_ids,
            proof,
        )

    def _replay_generated_operation(
        self,
        operation: PanelAwarePageGenerationOperation,
        admission_fence: PageExecutionFencePort,
    ) -> PanelAwarePageGenerationResult:
        accepted: list[tuple[PanelAsset, PanelGenerationEvidence, bytes]] = []
        for unit in operation.panel_units:
            recovered = self._accepted_existing(unit)
            if recovered is None:
                return _result(
                    "blocked",
                    "generated_replay_panel_proof_unavailable",
                    0,
                    tuple(item[0].panel_id for item in accepted),
                )
            accepted.append(recovered)
        if len(accepted) != operation.plan.panel_count:
            return _result(
                "blocked",
                "generated_replay_panel_set_incomplete",
                0,
                tuple(item[0].panel_id for item in accepted),
            )
        try:
            request = PageCompositionRequest(
                composition_attempt_id=operation.composition_attempt_id,
                plan_id=operation.plan.plan_id,
                plan_fingerprint=operation.plan.plan_fingerprint or "",
                project_id=operation.plan.project_id,
                page_id=operation.plan.page_id,
                explicit_authorization_reference=(
                    operation.composition_authorization_reference
                ),
                composition_provenance_reference=(
                    operation.composition_provenance_reference
                ),
                margins=operation.plan.margins,
                gutter_px=operation.plan.gutter_px,
                panel_count=operation.plan.panel_count,
                sources=_accepted_sources(operation.plan, accepted),
            )
        except ValueError:
            return _result(
                "blocked",
                "generated_replay_composition_set_invalid",
                0,
                tuple(item[0].panel_id for item in accepted),
            )
        existing = self._composition_authority.lookup(
            request.composition_attempt_id
        )
        if existing.outcome != "confirmed":
            return _result(
                "blocked",
                "generated_replay_composition_unavailable",
                0,
                tuple(item[0].panel_id for item in accepted),
            )
        return self._resume_existing_composition(
            operation,
            request,
            existing,
            0,
            tuple(item[0].panel_id for item in accepted),
            admission_fence,
            applied_only=True,
        )

    def _accepted_existing(
        self, unit: PanelGenerationUnit
    ) -> tuple[PanelAsset, PanelGenerationEvidence, bytes] | None:
        found = self._panel_authority.lookup_attempt(unit.reservation.attempt_id)
        if (
            found.outcome != "confirmed"
            or found.record is None
            or found.record.reservation != unit.reservation
            or found.record.state != "PANEL_ACCEPTED"
        ):
            return None
        evidence_result = self._panel_authority.lookup_evidence(
            unit.reservation.attempt_id
        )
        evidence = evidence_result.evidence
        if (
            evidence_result.outcome != "found"
            or evidence is None
            or evidence.outcome != "accepted"
            or evidence.output_asset_id is None
            or evidence.output_sha256 is None
            or evidence.width is None
            or evidence.height is None
            or not _accepted_evidence_matches_unit(unit, evidence)
        ):
            return None
        asset = PanelAsset(
            asset_id=evidence.output_asset_id,
            plan_id=evidence.plan_id,
            plan_fingerprint=evidence.plan_fingerprint,
            project_id=evidence.project_id,
            page_id=evidence.page_id,
            panel_id=evidence.panel_id,
            panel_order=evidence.panel_order,
            request_id=evidence.request_id,
            request_fingerprint=evidence.request_fingerprint,
            attempt_id=evidence.attempt_id,
            width=evidence.width,
            height=evidence.height,
            content_sha256=evidence.output_sha256,
        )
        image_bytes = self._panel_reader.read(asset)
        if image_bytes is None or hashlib.sha256(image_bytes).hexdigest() != asset.content_sha256:
            return None
        return asset, evidence, image_bytes

    def _commit_failed_composition(
        self,
        operation: PanelAwarePageGenerationOperation,
        request: PageCompositionRequest,
        outcome: Literal["failed", "recovery_required"],
    ) -> bool:
        try:
            evidence = PageCompositionEvidence(
                evidence_id=operation.composition_evidence_id,
                composition_attempt_id=request.composition_attempt_id,
                plan_id=request.plan_id,
                plan_fingerprint=request.plan_fingerprint,
                project_id=request.project_id,
                page_id=request.page_id,
                request_fingerprint=request.request_fingerprint or "",
                composition_provenance_reference=(
                    request.composition_provenance_reference
                ),
                ordered_sources=request.sources,
                outcome=outcome,
            )
            committed = self._composition_authority.commit_evidence(evidence)
            if committed.outcome not in {"updated", "confirmed"}:
                return False
            verified = self._composition_authority.lookup(
                request.composition_attempt_id
            )
            return (
                verified.outcome == "confirmed"
                and verified.attempt is not None
                and verified.evidence == evidence
                and verified.attempt.outcome == outcome
            )
        except Exception:
            return False


def _panel_terminal_is_durable(
    authority: LocalPanelGenerationAuthority,
    reservation: PanelAttemptReservation,
    transition: PanelGenerationAuthorityResult,
    expected_state: Literal["DECLARED_FAILURE"],
) -> bool:
    if transition.outcome not in {"updated", "confirmed"}:
        return False
    try:
        verified = authority.lookup_attempt(reservation.attempt_id)
    except Exception:
        return False
    return (
        verified.outcome == "confirmed"
        and verified.record is not None
        and verified.record.reservation == reservation
        and verified.record.state == expected_state
        and verified.record.provider_start_consumed
    )


def _require_panel_recovery_durable(
    authority: LocalPanelGenerationAuthority,
    reservation: PanelAttemptReservation,
) -> bool:
    try:
        transition = authority.require_recovery(reservation)
    except Exception:
        return False
    if transition.outcome not in {"updated", "confirmed"}:
        return False
    try:
        verified = authority.lookup_attempt(reservation.attempt_id)
    except Exception:
        return False
    return (
        verified.outcome == "confirmed"
        and verified.record is not None
        and verified.record.reservation == reservation
        and verified.record.state == "RECOVERY_REQUIRED"
        and verified.record.provider_start_consumed
    )


def _composition_attempt_matches_request(
    attempt: PageCompositionAttempt,
    request: PageCompositionRequest,
) -> bool:
    return (
        attempt.composition_attempt_id == request.composition_attempt_id
        and attempt.request_fingerprint == request.request_fingerprint
        and attempt.plan_id == request.plan_id
        and attempt.plan_fingerprint == request.plan_fingerprint
        and attempt.project_id == request.project_id
        and attempt.page_id == request.page_id
        and attempt.explicit_authorization_reference
        == request.explicit_authorization_reference
        and attempt.composition_provenance_reference
        == request.composition_provenance_reference
        and attempt.compositor_profile_id == request.compositor_profile_id
        and attempt.compositor_profile_version == request.compositor_profile_version
        and attempt.ordered_source_asset_ids
        == tuple(source.asset_id for source in request.sources)
        and attempt.ordered_source_hashes
        == tuple(source.content_sha256 for source in request.sources)
    )


def _composition_evidence_matches_request(
    operation: PanelAwarePageGenerationOperation,
    request: PageCompositionRequest,
    evidence: PageCompositionEvidence,
    expected_outcome: Literal["reserved", "completed", "failed", "recovery_required"],
) -> bool:
    return expected_outcome != "reserved" and (
        evidence.evidence_id == operation.composition_evidence_id
        and evidence.composition_attempt_id == request.composition_attempt_id
        and evidence.plan_id == request.plan_id
        and evidence.plan_fingerprint == request.plan_fingerprint
        and evidence.project_id == request.project_id
        and evidence.page_id == request.page_id
        and evidence.request_fingerprint == request.request_fingerprint
        and evidence.composition_provenance_reference
        == request.composition_provenance_reference
        and evidence.ordered_sources == request.sources
        and evidence.outcome == expected_outcome
        and evidence.provider_invocation_performed is False
        and evidence.operation_kind == "deterministic_page_composition"
    )


def _operation_matches(operation: PanelAwarePageGenerationOperation) -> bool:
    plan = operation.plan
    claim = operation.mode_claim
    if (
        claim.mode != "panel_aware"
        or claim.project_id != plan.project_id
        or claim.page_id != plan.page_id
        or claim.page_revision != operation.page_revision
        or claim.mode_binding_reference != plan.plan_id
        or len(operation.panel_units) != plan.panel_count
    ):
        return False
    for panel, unit in zip(plan.panels, operation.panel_units, strict=True):
        request = unit.request
        reservation = unit.reservation
        if (
            request.plan_id != plan.plan_id
            or request.plan_fingerprint != plan.plan_fingerprint
            or request.project_id != plan.project_id
            or request.page_id != plan.page_id
            or request.panel_id != panel.panel_id
            or request.panel_order != panel.order
            or request.panel_prompt != panel
            or reservation.plan_id != request.plan_id
            or reservation.plan_fingerprint != request.plan_fingerprint
            or reservation.project_id != request.project_id
            or reservation.page_id != request.page_id
            or reservation.panel_id != request.panel_id
            or reservation.panel_order != request.panel_order
            or reservation.request_id != request.request_id
            or reservation.request_fingerprint != request.request_fingerprint
        ):
            return False
    return True


def _successful_panel_matches(
    unit: PanelGenerationUnit, execution: PanelProviderExecution
) -> bool:
    asset = execution.asset
    evidence = execution.evidence
    image_bytes = execution.image_bytes
    if asset is None or evidence is None or image_bytes is None:
        return False
    reservation = unit.reservation
    expected = (
        reservation.plan_id,
        reservation.plan_fingerprint,
        reservation.project_id,
        reservation.page_id,
        reservation.panel_id,
        reservation.panel_order,
        reservation.request_id,
        reservation.request_fingerprint,
        reservation.attempt_id,
    )
    asset_binding = (
        asset.plan_id,
        asset.plan_fingerprint,
        asset.project_id,
        asset.page_id,
        asset.panel_id,
        asset.panel_order,
        asset.request_id,
        asset.request_fingerprint,
        asset.attempt_id,
    )
    evidence_binding = (
        evidence.plan_id,
        evidence.plan_fingerprint,
        evidence.project_id,
        evidence.page_id,
        evidence.panel_id,
        evidence.panel_order,
        evidence.request_id,
        evidence.request_fingerprint,
        evidence.attempt_id,
    )
    return (
        asset_binding == expected == evidence_binding
        and evidence.outcome == "accepted"
        and evidence.output_asset_id == asset.asset_id
        and evidence.output_sha256 == asset.content_sha256
        and evidence.width == asset.width
        and evidence.height == asset.height
        and hashlib.sha256(image_bytes).hexdigest() == asset.content_sha256
    )


def _accepted_evidence_matches_unit(
    unit: PanelGenerationUnit,
    evidence: PanelGenerationEvidence,
) -> bool:
    reservation = unit.reservation
    request = unit.request
    return (
        (
            evidence.plan_id,
            evidence.plan_fingerprint,
            evidence.project_id,
            evidence.page_id,
            evidence.panel_id,
            evidence.panel_order,
            evidence.request_id,
            evidence.request_fingerprint,
            evidence.attempt_id,
        )
        == (
            reservation.plan_id,
            reservation.plan_fingerprint,
            reservation.project_id,
            reservation.page_id,
            reservation.panel_id,
            reservation.panel_order,
            reservation.request_id,
            reservation.request_fingerprint,
            reservation.attempt_id,
        )
        and evidence.input_reference == request.input_reference
        and evidence.input_sha256 == request.input_sha256
        and evidence.provenance_reference == request.provenance_reference
        and evidence.provider_reference == reservation.provider_reference
    )


def _accepted_sources(
    plan: PageGenerationPlan,
    accepted: list[tuple[PanelAsset, PanelGenerationEvidence, bytes]],
) -> tuple[AcceptedPanelSource, ...]:
    sources: list[AcceptedPanelSource] = []
    for panel, (asset, evidence, _image_bytes) in zip(
        plan.panels, accepted, strict=True
    ):
        sources.append(
            AcceptedPanelSource(
                plan_id=asset.plan_id,
                plan_fingerprint=asset.plan_fingerprint,
                project_id=asset.project_id,
                page_id=asset.page_id,
                panel_id=asset.panel_id,
                panel_order=asset.panel_order,
                request_id=asset.request_id,
                request_fingerprint=asset.request_fingerprint,
                attempt_id=asset.attempt_id,
                evidence_id=evidence.evidence_id,
                asset_id=asset.asset_id,
                content_sha256=asset.content_sha256,
                width=asset.width,
                height=asset.height,
                rectangle=panel.rectangle,
            )
        )
    return tuple(sources)


def _result(
    status: Literal["generated", "partial", "blocked", "recovery_required"],
    code: str,
    provider_calls: int,
    accepted_panel_ids: tuple[str, ...],
) -> PanelAwarePageGenerationResult:
    return PanelAwarePageGenerationResult(
        status, code, provider_calls, accepted_panel_ids
    )
