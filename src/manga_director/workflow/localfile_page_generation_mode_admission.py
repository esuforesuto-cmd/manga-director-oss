"""Shared-fence admission for one private Page generation mode."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal, Protocol, TypeVar, cast

from manga_director.production.next_generation_deterministic_composite_asset_owner import (
    DeterministicCompositeAssetOwner,
)
from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    DurableEvidenceWorkflowBindingReport,
    WorkflowApplicationAuthorizationDTO,
)
from manga_director.production.next_generation_generation_evidence_persistence import (
    GenerationEvidenceInventoryObservation,
    LocalGenerationEvidenceStore,
)
from manga_director.production.next_generation_local_durable_asset_owner import (
    DurableAssetInventoryObservation,
    LocalDurableAssetOwner,
)
from manga_director.production.next_generation_normal_execution_attempt import (
    LocalNormalExecutionAttemptStore,
    NormalExecutionAttemptRecord,
    NormalExecutionAttemptReservationDTO,
    NormalExecutionAttemptStoreResult,
)
from manga_director.production.next_generation_page_composition import (
    AcceptedPanelSource,
    LocalPageCompositionAuthority,
)
from manga_director.production.next_generation_page_composition_application_ledger import (
    LocalPageCompositionApplicationLedger,
)
from manga_director.production.next_generation_page_generation_mode_claim import (
    LocalPageGenerationModeClaimStore,
    PageGenerationModeClaim,
)
from manga_director.production.next_generation_page_output_proof import (
    PageOutputApplicationAdmission,
    ProviderGenerationPageOutputProof,
)
from manga_director.production.next_generation_panel_generation_evidence import (
    LocalPanelGenerationAuthority,
    PanelGenerationEvidence,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    LocalWorkflowApplicationLedgerStore,
    WorkflowApplicationInventoryObservation,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow.durable_execution import LocalFileDurablePageStore
from manga_director.workflow.page_execution_fence import PageExecutionFencePort

_AdmittedActionResult = TypeVar("_AdmittedActionResult")
_MODE_CLAIMS = "page-generation-mode-claims"
_PANEL_AUTHORITY = "panel-generation-authority"
_COMPOSITION_AUTHORITY = "page-composition-authority"
_COMPOSITE_OWNER = "deterministic-composite-owner"
_COMPOSITION_APPLICATION = "page-composition-application"


@dataclass(frozen=True, slots=True)
class PageGenerationModeObservation:
    """Authoritative Page and durable record facts observed under the fence."""

    project_id: str
    page_id: str
    page_revision: str
    page_fingerprint: str
    page_state: str
    output_asset_id: str | None = None
    legacy_record_references: tuple[str, ...] = ()
    panel_record_references: tuple[str, ...] = ()
    legacy_candidate_count: int = 0
    legacy_reconciliation_eligible: bool = True


class PageGenerationModeObservationPort(Protocol):
    def observe(
        self, project_id: str, page_id: str
    ) -> PageGenerationModeObservation | None: ...


class LocalFilePageGenerationModeObservation:
    """Compose owner-verified Page records without exposing storage details."""

    def __init__(self, repository: LocalFileRepository) -> None:
        self._repository = repository
        self._page_store = LocalFileDurablePageStore(repository)
        self._normal_root = repository._next_generation_normal_execution_owner_root()

    @property
    def claim_root(self) -> Path:
        return self._normal_root / _MODE_CLAIMS

    def observe(
        self, project_id: str, page_id: str
    ) -> PageGenerationModeObservation | None:
        try:
            normalized_page_id = str(int(page_id))
            snapshot = self._page_store.load_revisioned(project_id)
            page = snapshot.project.page(int(normalized_page_id))
            page_revision = f"revision-{snapshot.revision}"
            output_asset_id = None
            if isinstance(page.image, dict):
                candidate = page.image.get("output_asset_id")
                if isinstance(candidate, str) and candidate:
                    output_asset_id = candidate
            panel_observation = self._panel_records(
                project_id,
                normalized_page_id,
                page_revision,
                page.state.value,
                output_asset_id,
            )
            if panel_observation is None:
                return None
            panel, panel_authority_attempt_ids = panel_observation
            legacy_observation = self._legacy_records(
                project_id,
                normalized_page_id,
                page_revision,
                page.state.value,
                output_asset_id,
                panel_authority_attempt_ids,
            )
            if legacy_observation is None:
                return None
            legacy, legacy_candidate_count, legacy_reconciliation_eligible = (
                legacy_observation
            )
            return PageGenerationModeObservation(
                project_id=project_id,
                page_id=normalized_page_id,
                page_revision=page_revision,
                page_fingerprint=snapshot.fingerprint,
                page_state=page.state.value,
                output_asset_id=output_asset_id,
                legacy_record_references=legacy,
                panel_record_references=panel,
                legacy_candidate_count=legacy_candidate_count,
                legacy_reconciliation_eligible=legacy_reconciliation_eligible,
            )
        except Exception:
            return None

    def _legacy_records(
        self,
        project_id: str,
        page_id: str,
        page_revision: str,
        page_state: str,
        output_asset_id: str | None,
        panel_authority_attempt_ids: tuple[str, ...],
    ) -> tuple[tuple[str, ...], int, bool] | None:
        application_page = LocalWorkflowApplicationLedgerStore.observe_page(
            self._repository._workflow_application_ledger_owner_root(),
            project_id,
            page_id,
        )
        if application_page.outcome in {"corrupt", "ambiguous", "prepared"}:
            return None
        attempts = LocalNormalExecutionAttemptStore(
            self._normal_root / "attempts"
        ).observe_page(project_id, page_id)
        if attempts.outcome == "corrupt":
            return None
        evidence_presence = LocalGenerationEvidenceStore.observe_presence(
            self._normal_root / "evidence", attempts.authority_attempt_ids
        )
        asset_presence = LocalDurableAssetOwner.observe_presence(
            self._normal_root / "assets",
            tuple(
                sorted(
                    set(attempts.authority_attempt_ids)
                    | set(panel_authority_attempt_ids)
                )
            ),
        )
        if evidence_presence.outcome in {"orphaned", "corrupt"} or (
            asset_presence.outcome in {"orphaned", "corrupt"}
        ):
            return None
        if attempts.outcome == "missing" and application_page.outcome == "missing":
            return (), 0, True
        attempt_ids = tuple(
            sorted(
                {
                    *(record.reservation.attempt_id for record in attempts.records),
                    *application_page.attempt_ids,
                }
            )
        )
        evidence = LocalGenerationEvidenceStore.observe_attempts(
            self._normal_root / "evidence", attempt_ids
        )
        assets = LocalDurableAssetOwner.observe_attempts(
            self._normal_root / "assets", attempt_ids
        )
        application = LocalWorkflowApplicationLedgerStore.observe_attempts(
            self._repository._workflow_application_ledger_owner_root(),
            attempt_ids,
        )
        related = (evidence, assets, application)
        if any(item.outcome in {"corrupt", "prepared"} for item in related):
            return None
        if application_page.outcome == "found" and (
            application.outcome != "found"
            or application.attempt_ids != application_page.attempt_ids
            or application.bindings != application_page.bindings
        ):
            return None
        if application_page.outcome == "missing" and application.outcome != "missing":
            return None
        if not _legacy_lifecycle_matrix_matches(
            attempts.records,
            evidence,
            assets,
            application,
            page_state,
            output_asset_id,
            require_known_output_hash=False,
        ):
            return None
        reconciliation_eligible = _legacy_lifecycle_matrix_matches(
            attempts.records,
            evidence,
            assets,
            application,
            page_state,
            output_asset_id,
            require_known_output_hash=True,
        )
        binding_revision = page_revision
        if page_state == "Generated":
            try:
                revision_number = int(page_revision.removeprefix("revision-"))
            except ValueError:
                return None
            if revision_number <= 0:
                return None
            binding_revision = f"revision-{revision_number - 1}"
        return (
            (_legacy_mode_binding(project_id, page_id, binding_revision),),
            len(attempt_ids),
            reconciliation_eligible,
        )

    def _panel_records(
        self,
        project_id: str,
        page_id: str,
        page_revision: str,
        page_state: str,
        output_asset_id: str | None,
    ) -> tuple[tuple[str, ...], tuple[str, ...]] | None:
        panel = LocalPanelGenerationAuthority.observe_page_at(
            self._normal_root / _PANEL_AUTHORITY, project_id, page_id
        )
        composition = LocalPageCompositionAuthority.observe_page_at(
            self._normal_root / _COMPOSITION_AUTHORITY, project_id, page_id
        )
        application = LocalPageCompositionApplicationLedger.observe_page_at(
            self._normal_root / _COMPOSITION_APPLICATION, project_id, page_id
        )
        observations = (panel, composition, application)
        if any(item.outcome in {"corrupt", "ambiguous"} for item in observations):
            return None
        assets = DeterministicCompositeAssetOwner.observe_page_at(
            self._normal_root / _COMPOSITE_OWNER,
            project_id,
            page_id,
        )
        if assets.outcome in {"corrupt", "ambiguous"}:
            return None
        owner_attempt_ids = (
            assets.composition_attempt_ids if assets.outcome == "found" else ()
        )
        if set(owner_attempt_ids) != set(composition.attempt_ids):
            return None
        plan_ids = {
            plan_id
            for item in observations
            if item.outcome in {"found", "prepared"}
            for plan_id in item.plan_ids
        }
        if not plan_ids:
            return (), panel.authority_attempt_ids
        if len(plan_ids) != 1:
            return None
        panel_assets = LocalDurableAssetOwner.observe_attempts(
            self._normal_root / "assets", panel.attempt_ids
        )
        if panel_assets.outcome == "corrupt":
            return None
        if composition.outcome == "found" and panel.outcome != "found":
            return None
        if application.outcome in {"found", "prepared"} and composition.outcome != "found":
            return None
        if application.outcome in {"found", "prepared"} and any(
            attempt_id not in composition.attempt_ids
            for attempt_id in application.composition_attempt_ids
        ):
            return None
        if application.outcome in {"found", "prepared"} and (
            assets.outcome != "found"
            or any(
                attempt_id not in assets.composition_attempt_ids
                for attempt_id in application.composition_attempt_ids
            )
        ):
            return None
        if not _panel_chain_matches(
            panel,
            panel_assets,
            composition,
            assets,
            application,
            page_revision,
            page_state,
            output_asset_id,
        ):
            return None
        return tuple(plan_ids), panel.authority_attempt_ids


@dataclass(frozen=True, slots=True)
class PageGenerationModeAdmissionResult:
    outcome: Literal["admitted", "blocked"]
    code: str
    claim: PageGenerationModeClaim | None = field(default=None, repr=False)

    @property
    def admitted(self) -> bool:
        return self.outcome == "admitted"


class LocalFilePageGenerationModeAdmission:
    """Atomically observe, create-or-confirm, and reverify one exact claim."""

    def __init__(
        self,
        claim_store: LocalPageGenerationModeClaimStore,
        observation_port: PageGenerationModeObservationPort,
    ) -> None:
        self._claim_store = claim_store
        self._observation_port = observation_port

    def admit(
        self,
        claim: PageGenerationModeClaim,
        fence: PageExecutionFencePort,
    ) -> PageGenerationModeAdmissionResult:
        acquired = False
        try:
            fence.acquire()
            acquired = True
            return self._admit_locked(claim)
        except Exception:
            return PageGenerationModeAdmissionResult("blocked", "admission_unavailable")
        finally:
            if acquired:
                fence.release()

    def run_admitted(
        self,
        claim: PageGenerationModeClaim,
        fence: PageExecutionFencePort,
        action: Callable[[], _AdmittedActionResult],
    ) -> tuple[PageGenerationModeAdmissionResult, _AdmittedActionResult | None]:
        """Hold the same Page fence across final admission and one application."""

        acquired = False
        try:
            fence.acquire()
            acquired = True
            admission = self._admit_locked(claim)
            if not admission.admitted:
                return admission, None
            try:
                return admission, action()
            except Exception:
                return admission, None
        except Exception:
            return (
                PageGenerationModeAdmissionResult(
                    "blocked", "admitted_action_unavailable"
                ),
                None,
            )
        finally:
            if acquired:
                fence.release()

    def run_provider_start_admitted(
        self,
        claim: PageGenerationModeClaim,
        fence: PageExecutionFencePort,
        action: Callable[[], _AdmittedActionResult],
    ) -> tuple[PageGenerationModeAdmissionResult, _AdmittedActionResult | None]:
        """Recheck the Page and consume one Provider start under one fence."""

        acquired = False
        try:
            fence.acquire()
            acquired = True
            admission = self._admit_locked(claim)
            if not admission.admitted:
                return admission, None
            try:
                return admission, action()
            except Exception:
                return admission, None
        except Exception:
            return (
                PageGenerationModeAdmissionResult(
                    "blocked", "provider_start_admission_unavailable"
                ),
                None,
            )
        finally:
            if acquired:
                fence.release()

    def run_generated_replay_admitted(
        self,
        claim: PageGenerationModeClaim,
        fence: PageExecutionFencePort,
        expected_output_asset_id: str,
        action: Callable[[], _AdmittedActionResult],
    ) -> tuple[PageGenerationModeAdmissionResult, _AdmittedActionResult | None]:
        """Verify one already-Generated Page and its exact claim under the fence."""

        acquired = False
        try:
            fence.acquire()
            acquired = True
            before = self._observation_port.observe(claim.project_id, claim.page_id)
            code = _generated_replay_conflict(
                claim, before, expected_output_asset_id
            )
            if code is not None:
                return PageGenerationModeAdmissionResult("blocked", code), None
            lookup = self._claim_store.lookup_active(
                claim.project_id, claim.page_id, claim.page_revision
            )
            if lookup.outcome != "found" or lookup.claim != claim:
                return (
                    PageGenerationModeAdmissionResult(
                        "blocked", "generated_replay_claim_unavailable"
                    ),
                    None,
                )
            after = self._observation_port.observe(claim.project_id, claim.page_id)
            if after != before:
                return (
                    PageGenerationModeAdmissionResult(
                        "blocked", "page_authority_changed"
                    ),
                    None,
                )
            try:
                return (
                    PageGenerationModeAdmissionResult(
                        "admitted", "generated_replay_admitted", claim
                    ),
                    action(),
                )
            except Exception:
                return (
                    PageGenerationModeAdmissionResult(
                        "admitted", "generated_replay_admitted", claim
                    ),
                    None,
                )
        except Exception:
            return (
                PageGenerationModeAdmissionResult(
                    "blocked", "generated_replay_admission_unavailable"
                ),
                None,
            )
        finally:
            if acquired:
                fence.release()

    def _admit_locked(
        self, claim: PageGenerationModeClaim
    ) -> PageGenerationModeAdmissionResult:
        before = self._observation_port.observe(claim.project_id, claim.page_id)
        code = _observation_conflict(claim, before)
        if code is not None:
            return PageGenerationModeAdmissionResult("blocked", code)

        lookup = self._claim_store.lookup_active(
            claim.project_id, claim.page_id, claim.page_revision
        )
        if lookup.outcome == "found" and lookup.claim != claim:
            return PageGenerationModeAdmissionResult("blocked", "claim_conflict")
        if lookup.outcome not in {"found", "missing"}:
            return PageGenerationModeAdmissionResult("blocked", "claim_unavailable")

        stored = self._claim_store.create_or_confirm(claim)
        if stored.outcome not in {"created", "confirmed"}:
            return PageGenerationModeAdmissionResult("blocked", "claim_not_committed")

        after = self._observation_port.observe(claim.project_id, claim.page_id)
        if after != before:
            return PageGenerationModeAdmissionResult("blocked", "page_authority_changed")
        verified = self._claim_store.lookup_active(
            claim.project_id, claim.page_id, claim.page_revision
        )
        if verified.outcome != "found" or verified.claim != claim:
            return PageGenerationModeAdmissionResult("blocked", "claim_not_verified")
        return PageGenerationModeAdmissionResult("admitted", "admitted", claim)


def _admit_localfile_legacy_generation(  # noqa: C901 - closed reconciliation gate.
    repository: LocalFileRepository,
    project_id: str,
    page_id: str,
    attempt_id: str,
    authorized_by: str,
    fence: PageExecutionFencePort,
) -> tuple[
    LocalFilePageGenerationModeAdmission | None,
    PageGenerationModeAdmissionResult,
    PageGenerationModeClaim | None,
]:
    """Acquire or exactly reconcile one private legacy claim."""

    observation = LocalFilePageGenerationModeObservation(repository)
    observed = observation.observe(project_id, page_id)
    if observed is None:
        return None, PageGenerationModeAdmissionResult(
            "blocked", "authority_unavailable"
        ), None
    binding_revision = observed.page_revision
    if observed.page_state == "Generated":
        try:
            binding_revision = (
                f"revision-{int(observed.page_revision.removeprefix('revision-')) - 1}"
            )
        except ValueError:
            return None, PageGenerationModeAdmissionResult(
                "blocked", "generated_replay_revision_invalid"
            ), None
    binding_reference = _legacy_mode_binding(project_id, page_id, binding_revision)
    if observed.legacy_record_references not in {(), (binding_reference,)}:
        return None, PageGenerationModeAdmissionResult(
            "blocked", "legacy_reconciliation_mismatch"
        ), None
    digest = hashlib.sha256(
        f"{project_id}\0{page_id}\0{observed.page_revision}".encode()
    ).hexdigest()
    claim = PageGenerationModeClaim(
        claim_id=f"claim-v7-011-legacy-{digest[:32]}",
        project_id=project_id,
        page_id=page_id,
        page_revision=observed.page_revision,
        page_fingerprint=observed.page_fingerprint,
        mode="legacy_single_canvas",
        mode_binding_reference=binding_reference,
        authorizer_reference=_claim_reference("authorizer", authorized_by),
    )
    claim_store = LocalPageGenerationModeClaimStore(observation.claim_root)
    if observed.page_state == "Generated":
        try:
            revision_number = int(observed.page_revision.removeprefix("revision-"))
        except ValueError:
            return None, PageGenerationModeAdmissionResult(
                "blocked", "generated_replay_revision_invalid"
            ), None
        lookup = claim_store.lookup_active(
            project_id, page_id, f"revision-{revision_number - 1}"
        )
        existing_claim = lookup.claim
        if (
            lookup.outcome != "found"
            or existing_claim is None
            or existing_claim.mode != "legacy_single_canvas"
            or observed.output_asset_id is None
        ):
            return None, PageGenerationModeAdmissionResult(
                "blocked", "generated_replay_claim_unavailable"
            ), None
        service = LocalFilePageGenerationModeAdmission(claim_store, observation)
        replay_result, confirmed = service.run_generated_replay_admitted(
            existing_claim,
            fence,
            observed.output_asset_id,
            lambda: True,
        )
        if not replay_result.admitted or confirmed is not True:
            return None, replay_result, None
        return service, replay_result, existing_claim
    if observed.page_state != "PromptBuilt":
        return None, PageGenerationModeAdmissionResult(
            "blocked", "legacy_source_state_mismatch"
        ), None
    existing = claim_store.lookup_active(project_id, page_id, observed.page_revision)
    if (
        observed.legacy_record_references
        and not observed.legacy_reconciliation_eligible
    ):
        return None, PageGenerationModeAdmissionResult(
            "blocked", "legacy_reconciliation_incomplete"
        ), None
    if observed.legacy_candidate_count > 1:
        if existing.outcome == "missing":
            return None, PageGenerationModeAdmissionResult(
                "blocked", "legacy_reconciliation_ambiguous"
            ), None
    service = LocalFilePageGenerationModeAdmission(claim_store, observation)
    return service, service.admit(claim, fence), claim


def _claim_reference(kind: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"{kind}-{digest}"


def _legacy_mode_binding(project_id: str, page_id: str, page_revision: str) -> str:
    return _claim_reference(
        "legacy-page", f"{project_id}\0{page_id}\0{page_revision}"
    )


def _legacy_output_chain_matches(
    evidence: GenerationEvidenceInventoryObservation,
    assets: DurableAssetInventoryObservation,
    records: tuple[NormalExecutionAttemptRecord, ...],
    *,
    require_known_output_hash: bool,
) -> bool:
    if (
        len(evidence.evidence) != len(evidence.provider_references)
        or len(evidence.evidence) != len(assets.bindings)
    ):
        return False
    asset_by_attempt = {item.attempt_id: item for item in assets.bindings}
    record_by_attempt = {
        item.reservation.attempt_id: item for item in records
    }
    for item, provider_reference in zip(
        evidence.evidence, evidence.provider_references, strict=True
    ):
        asset = asset_by_attempt.get(item.attempt_id)
        record = record_by_attempt.get(item.attempt_id)
        if (
            asset is None
            or record is None
            or provider_reference != record.reservation.provider_reference
            or asset.provider_reference != provider_reference
            or asset.output_asset_id != item.output.output_asset_id
            or asset.media_type != item.output.media_type
            or not (
                _evidence_sha256_matches(
                    item.output.output_content_hash, asset.content_sha256
                )
                if require_known_output_hash
                else _optional_evidence_sha256_matches(
                    item.output.output_content_hash, asset.content_sha256
                )
            )
        ):
            return False
    return True


def _known_sha256(value: object) -> str | None:
    digest = getattr(value, "value", None)
    if (
        getattr(value, "availability", None) != "known"
        or not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        return None
    return digest


def _evidence_sha256_matches(value: object, expected: str) -> bool:
    return _known_sha256(value) == expected


def _optional_evidence_sha256_matches(value: object, expected: str) -> bool:
    return value is None or _evidence_sha256_matches(value, expected)


def _legacy_application_chain_matches(
    project_id: str,
    page_id: str,
    application: WorkflowApplicationInventoryObservation,
    assets: DurableAssetInventoryObservation,
    records: tuple[NormalExecutionAttemptRecord, ...],
) -> bool:
    if len(application.bindings) != len(assets.bindings):
        return False
    asset_by_attempt = {item.attempt_id: item for item in assets.bindings}
    record_by_attempt = {
        item.reservation.attempt_id: item for item in records
    }
    return all(
        binding.project_id == project_id
        and binding.page_id == page_id
        and (asset := asset_by_attempt.get(binding.attempt_id)) is not None
        and (record := record_by_attempt.get(binding.attempt_id)) is not None
        and binding.target_page_reference
        == record.reservation.target_page_reference
        and binding.provider_reference == record.reservation.provider_reference
        and binding.provider_reference == asset.provider_reference
        and binding.output_asset_id == asset.output_asset_id
        and binding.source_state == "PromptBuilt"
        and binding.target_state == "Generated"
        for binding in application.bindings
    )


def _legacy_lifecycle_matrix_matches(  # noqa: C901 - closed lifecycle matrix.
    records: tuple[NormalExecutionAttemptRecord, ...],
    evidence: GenerationEvidenceInventoryObservation,
    assets: DurableAssetInventoryObservation,
    application: WorkflowApplicationInventoryObservation,
    page_state: str,
    output_asset_id: str | None,
    *,
    require_known_output_hash: bool = True,
) -> bool:
    """Require one complete legacy lifecycle shape; partial contradictions fail closed."""

    if not records:
        return False
    if sum(record.state != "COMPLETED" for record in records) > 1:
        return False
    evidence_attempts = {item.attempt_id for item in evidence.evidence}
    asset_attempts = {item.attempt_id for item in assets.bindings}
    application_attempts = {item.attempt_id for item in application.bindings}
    record_attempts = {item.reservation.attempt_id for item in records}
    if (
        len(record_attempts) != len(records)
        or evidence_attempts != set(evidence.attempt_ids)
        or asset_attempts != set(assets.attempt_ids)
        or application_attempts != set(application.attempt_ids)
        or not evidence_attempts.issubset(asset_attempts)
        or not asset_attempts.issubset(record_attempts)
        or not application_attempts.issubset(evidence_attempts)
    ):
        return False
    has_evidence = bool(evidence_attempts)
    has_asset = bool(asset_attempts)
    has_application = bool(application_attempts)
    if has_evidence and (
        not has_asset
        or not _legacy_output_chain_matches(
            evidence,
            assets,
            records,
            require_known_output_hash=require_known_output_hash,
        )
    ):
        return False
    if has_application and (
        not has_evidence
        or not has_asset
        or not _legacy_application_chain_matches(
            records[0].reservation.project_id,
            records[0].reservation.page_id,
            application,
            assets,
            records,
        )
    ):
        return False
    for record in records:
        attempt_id = record.reservation.attempt_id
        record_has_evidence = attempt_id in evidence_attempts
        record_has_asset = attempt_id in asset_attempts
        record_has_application = attempt_id in application_attempts
        if record.state in {"RESERVED", "PROVIDER_STARTED"}:
            if (
                record.completion_kind is not None
                or record_has_evidence
                or record_has_asset
                or record_has_application
            ):
                return False
        elif record.state == "PROVIDER_COMPLETED":
            if (
                record.completion_kind is not None
                or (record_has_evidence and not record_has_asset)
                or (record_has_application and not record_has_evidence)
            ):
                return False
        elif record.state == "COMPLETED":
            if record.completion_kind == "provider_declared_failure":
                if record_has_evidence or record_has_asset or record_has_application:
                    return False
            elif record.completion_kind == "application_event_published":
                if not (
                    record_has_evidence
                    and record_has_asset
                    and record_has_application
                ):
                    return False
            else:
                return False
        else:
            return False
    if has_application:
        applied_attempt_id = (
            application.bindings[0].attempt_id
            if len(application.bindings) == 1
            else ""
        )
        applied_record = next(
            (
                record
                for record in records
                if record.reservation.attempt_id == applied_attempt_id
            ),
            None,
        )
        return (
            len(application.bindings) == 1
            and applied_record is not None
            and (
                applied_record.state == "PROVIDER_COMPLETED"
                or (
                    applied_record.state == "COMPLETED"
                    and applied_record.completion_kind
                    == "application_event_published"
                )
            )
            and all(
                record is applied_record
                or (
                    record.state == "COMPLETED"
                    and record.completion_kind == "provider_declared_failure"
                )
                for record in records
            )
            and page_state == "Generated"
            and output_asset_id == application.bindings[0].output_asset_id
        )
    return page_state == "PromptBuilt" and output_asset_id is None


def _panel_chain_matches(  # noqa: C901 - closed cross-authority binding matrix.
    panel: object,
    panel_assets: DurableAssetInventoryObservation,
    composition: object,
    assets: object | None,
    application: object,
    page_revision: str,
    page_state: str,
    output_asset_id: str | None,
) -> bool:
    """Cross-check canonical Panel/composition/application owner facts exactly."""

    panel_records = tuple(getattr(panel, "records", ()))
    panel_evidence = tuple(getattr(panel, "evidence", ()))
    composition_attempts = tuple(getattr(composition, "attempts", ()))
    composition_evidence = tuple(getattr(composition, "evidence", ()))
    composite_assets = tuple(getattr(assets, "assets", ())) if assets else ()
    application_bindings = tuple(getattr(application, "bindings", ()))

    record_by_attempt = {
        item.reservation.attempt_id: item for item in panel_records
    }
    panel_asset_by_attempt = {
        item.attempt_id: item for item in panel_assets.bindings
    }
    if (
        len(record_by_attempt) != len(panel_records)
        or len(panel_asset_by_attempt) != len(panel_assets.bindings)
        or set(panel_asset_by_attempt) != set(panel_assets.attempt_ids)
        or set(panel_asset_by_attempt)
        != {
            item.reservation.attempt_id
            for item in panel_records
            if item.output_asset_id is not None
        }
    ):
        return False
    evidence_by_asset = {}
    accepted_by_panel: dict[tuple[str, int], PanelGenerationEvidence] = {}
    for item in panel_evidence:
        record = record_by_attempt.get(item.attempt_id)
        registered = panel_asset_by_attempt.get(item.attempt_id)
        if (
            record is None
            or record.state not in {"EVIDENCE_COMMITTED", "PANEL_ACCEPTED"}
            or item.outcome != "accepted"
            or item.output_asset_id is None
            or item.output_sha256 is None
            or registered is None
            or registered.provider_reference
            != record.reservation.provider_reference
            or registered.output_asset_id != record.output_asset_id
            or registered.output_asset_id != item.output_asset_id
            or registered.content_sha256 != item.output_sha256
            or registered.media_type != item.media_type
        ):
            return False
        if item.output_asset_id in evidence_by_asset:
            return False
        evidence_by_asset[item.output_asset_id] = item
        if record.state == "PANEL_ACCEPTED":
            panel_key = (item.panel_id, item.panel_order)
            if panel_key in accepted_by_panel:
                return False
            accepted_by_panel[panel_key] = item

    for record in panel_records:
        registered = panel_asset_by_attempt.get(record.reservation.attempt_id)
        if record.output_asset_id is None:
            if registered is not None:
                return False
            continue
        if (
            registered is None
            or registered.output_asset_id != record.output_asset_id
            or registered.provider_reference != record.reservation.provider_reference
            or registered.media_type != "image/png"
        ):
            return False

    canonical_accepted = tuple(
        accepted_by_panel[key]
        for key in sorted(accepted_by_panel, key=lambda item: item[1])
    )
    canonical_asset_ids = tuple(item.output_asset_id for item in canonical_accepted)
    canonical_hashes = tuple(item.output_sha256 for item in canonical_accepted)
    panel_plan_bindings = {
        (item.reservation.plan_id, item.reservation.plan_fingerprint)
        for item in panel_records
    }
    if len(panel_plan_bindings) != 1:
        return False
    panel_plan_id, panel_plan_fingerprint = next(iter(panel_plan_bindings))

    composition_by_attempt = {
        item.composition_attempt_id: item for item in composition_attempts
    }
    composition_evidence_by_attempt = {
        item.composition_attempt_id: item for item in composition_evidence
    }
    asset_by_attempt = {
        item.composition_attempt_id: item for item in composite_assets
    }
    if (
        len(composition_by_attempt) != len(composition_attempts)
        or len(composition_evidence_by_attempt) != len(composition_evidence)
        or len(asset_by_attempt) != len(composite_assets)
        or set(asset_by_attempt)
        != set(getattr(assets, "composition_attempt_ids", ()))
        or set(getattr(assets, "missing_composition_attempt_ids", ()))
        != set(composition_by_attempt) - set(asset_by_attempt)
        or set(asset_by_attempt) - set(composition_by_attempt)
    ):
        return False

    def sources_match_panel_evidence(
        sources: tuple[AcceptedPanelSource, ...],
    ) -> bool:
        if (
            tuple(getattr(source, "asset_id", None) for source in sources)
            != canonical_asset_ids
            or tuple(getattr(source, "content_sha256", None) for source in sources)
            != canonical_hashes
        ):
            return False
        for source in sources:
            panel_item = evidence_by_asset.get(getattr(source, "asset_id", None))
            if panel_item is None or (
                source.plan_id != panel_item.plan_id
                or source.plan_fingerprint != panel_item.plan_fingerprint
                or source.project_id != panel_item.project_id
                or source.page_id != panel_item.page_id
                or source.panel_id != panel_item.panel_id
                or source.panel_order != panel_item.panel_order
                or source.request_id != panel_item.request_id
                or source.request_fingerprint != panel_item.request_fingerprint
                or source.attempt_id != panel_item.attempt_id
                or source.evidence_id != panel_item.evidence_id
                or source.content_sha256 != panel_item.output_sha256
                or source.media_type != panel_item.media_type
                or source.width != panel_item.width
                or source.height != panel_item.height
            ):
                return False
        return True

    panel_pages = {
        (item.reservation.project_id, item.reservation.page_id)
        for item in panel_records
    }
    if len(panel_pages) != 1:
        return False
    panel_project_id, panel_page_id = next(iter(panel_pages))

    for attempt_id, attempt in composition_by_attempt.items():
        if (
            attempt.plan_id != panel_plan_id
            or attempt.plan_fingerprint != panel_plan_fingerprint
            or attempt.project_id != panel_project_id
            or attempt.page_id != panel_page_id
            or attempt.ordered_source_asset_ids != canonical_asset_ids
            or attempt.ordered_source_hashes != canonical_hashes
        ):
            return False
        evidence = composition_evidence_by_attempt.get(attempt_id)
        asset = asset_by_attempt.get(attempt_id)
        if asset is not None and (
            asset.composition_attempt_id != attempt_id
            or asset.request_fingerprint != attempt.request_fingerprint
            or asset.composition_provenance_reference
            != attempt.composition_provenance_reference
            or tuple(source.asset_id for source in asset.ordered_sources)
            != attempt.ordered_source_asset_ids
            or tuple(source.content_sha256 for source in asset.ordered_sources)
            != attempt.ordered_source_hashes
            or not sources_match_panel_evidence(asset.ordered_sources)
        ):
            return False
        if evidence is None:
            if attempt.outcome != "reserved":
                return False
            continue
        if (
            evidence.composition_attempt_id != attempt_id
            or evidence.plan_id != attempt.plan_id
            or evidence.plan_fingerprint != attempt.plan_fingerprint
            or evidence.project_id != attempt.project_id
            or evidence.page_id != attempt.page_id
            or evidence.request_fingerprint != attempt.request_fingerprint
            or evidence.composition_provenance_reference
            != attempt.composition_provenance_reference
            or tuple(source.asset_id for source in evidence.ordered_sources)
            != attempt.ordered_source_asset_ids
            or tuple(source.content_sha256 for source in evidence.ordered_sources)
            != attempt.ordered_source_hashes
            or not sources_match_panel_evidence(evidence.ordered_sources)
        ):
            return False
        if attempt.outcome == "completed":
            if asset is None or (
                evidence.outcome != "completed"
                or asset.request_fingerprint != attempt.request_fingerprint
                or asset.request_fingerprint != evidence.request_fingerprint
                or asset.composition_provenance_reference
                != attempt.composition_provenance_reference
                or asset.composition_provenance_reference
                != evidence.composition_provenance_reference
                or asset.ordered_sources != evidence.ordered_sources
                or asset.asset_id != evidence.output_asset_id
                or asset.content_sha256 != evidence.output_sha256
            ):
                return False
        elif asset is not None:
            return False

    for binding in application_bindings:
        attempt = composition_by_attempt.get(binding.composition_attempt_id)
        evidence = composition_evidence_by_attempt.get(binding.composition_attempt_id)
        asset = asset_by_attempt.get(binding.composition_attempt_id)
        if (
            attempt is None
            or attempt.outcome != "completed"
            or evidence is None
            or evidence.outcome != "completed"
            or asset is None
        ):
            return False
        evidence_sha256 = hashlib.sha256(
            json.dumps(
                evidence.model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest()
        if (
            binding.project_id != attempt.project_id
            or binding.page_id != attempt.page_id
            or binding.source_state != "PromptBuilt"
            or binding.target_state != "Generated"
            or binding.plan_id != attempt.plan_id
            or binding.plan_fingerprint != attempt.plan_fingerprint
            or binding.request_fingerprint != attempt.request_fingerprint
            or binding.composition_provenance_reference
            != attempt.composition_provenance_reference
            or binding.evidence_id != evidence.evidence_id
            or binding.evidence_sha256 != evidence_sha256
            or binding.composite_asset_id != asset.asset_id
            or binding.composite_sha256 != asset.content_sha256
        ):
            return False
    if application_bindings:
        if len(application_bindings) != 1:
            return False
        binding = application_bindings[0]
        if getattr(application, "outcome", None) == "prepared":
            return (
                binding.page_revision == page_revision
                and page_state == "PromptBuilt"
                and output_asset_id is None
            )
        if page_state != "Generated":
            return False
        try:
            revision_number = int(page_revision.removeprefix("revision-"))
        except ValueError:
            return False
        return (
            revision_number > 0
            and binding.page_revision == f"revision-{revision_number - 1}"
            and output_asset_id == binding.composite_asset_id
        )
    return page_state == "PromptBuilt" and output_asset_id is None


class _ModeGuardedAttemptStore:
    """Revalidate the mode claim when Provider start is consumed."""

    def __init__(
        self,
        delegate: LocalNormalExecutionAttemptStore,
        admission: LocalFilePageGenerationModeAdmission,
        claim: PageGenerationModeClaim,
        fence_factory: Callable[[str, str], PageExecutionFencePort],
    ) -> None:
        self._delegate = delegate
        self._admission = admission
        self._claim = claim
        self._fence_factory = fence_factory

    def reserve(
        self, reservation: NormalExecutionAttemptReservationDTO
    ) -> NormalExecutionAttemptStoreResult:
        return self._delegate.reserve(reservation)

    def start_provider(
        self, reservation: NormalExecutionAttemptReservationDTO
    ) -> NormalExecutionAttemptStoreResult:
        admitted, result = self._admission.run_provider_start_admitted(
            self._claim,
            self._fence_factory(self._claim.project_id, self._claim.page_id),
            lambda: self._delegate.start_provider(reservation),
        )
        if not admitted.admitted or not isinstance(
            result, NormalExecutionAttemptStoreResult
        ):
            return NormalExecutionAttemptStoreResult("invalid")
        return result

    def record_provider_success(
        self, reservation: NormalExecutionAttemptReservationDTO
    ) -> NormalExecutionAttemptStoreResult:
        return self._delegate.record_provider_success(reservation)

    def record_provider_declared_failure(
        self, reservation: NormalExecutionAttemptReservationDTO
    ) -> NormalExecutionAttemptStoreResult:
        return self._delegate.record_provider_declared_failure(reservation)

    def complete_after_application(
        self, reservation: NormalExecutionAttemptReservationDTO
    ) -> NormalExecutionAttemptStoreResult:
        return self._delegate.complete_after_application(reservation)

    def lookup(self, attempt_id: str) -> NormalExecutionAttemptRecord | None:
        return self._delegate.lookup(attempt_id)


@dataclass(frozen=True, slots=True)
class _BlockedProviderApplication:
    status: str = "application_blocked"


class _FenceFactoryOwner(Protocol):
    _fence_factory: Callable[[str, str], PageExecutionFencePort]


class _BorrowedPageFence:
    """Expose an already-held shared fence without acquiring or releasing twice."""

    def __init__(self, fence: PageExecutionFencePort) -> None:
        self._fence = fence

    def acquire(self) -> None:
        return None

    def release(self) -> None:
        return None

    def _r26_is_held_for(self, project_id: str, page_id: str) -> bool:
        check = getattr(self._fence, "_r26_is_held_for", None)
        return bool(callable(check) and check(project_id, page_id))


class _ProviderApplicationAdmission:
    """Require one exact legacy Provider proof before workflow delegation."""

    def __init__(
        self,
        delegate: object,
        evidence_store: LocalGenerationEvidenceStore,
        evidence_owner_root: Path,
        asset_owner_root: Path,
        admission: LocalFilePageGenerationModeAdmission,
        claim: PageGenerationModeClaim,
        fence_factory: Callable[[str, str], PageExecutionFencePort],
    ) -> None:
        self._delegate = delegate
        self._evidence_store = evidence_store
        self._evidence_owner_root = evidence_owner_root
        self._asset_owner_root = asset_owner_root
        self._admission = admission
        self._claim = claim
        self._fence_factory = fence_factory

    def apply(self, binding: object, authorization: object) -> object:
        attempt_id = getattr(binding, "attempt_id", "")
        lookup = self._evidence_store.lookup(attempt_id)
        evidence = lookup.generation_evidence
        output = getattr(evidence, "output", None)
        inventory = LocalGenerationEvidenceStore.observe_attempts(
            self._evidence_owner_root, (attempt_id,)
        )
        asset = LocalDurableAssetOwner.observe_output(
            self._asset_owner_root,
            attempt_id=attempt_id,
            provider_reference=getattr(binding, "provider_reference", ""),
            output_asset_id=getattr(binding, "output_asset_id", ""),
        )
        digest = asset.content_sha256
        valid = (
            lookup.outcome == "found"
            and evidence is not None
            and evidence.attempt_id == attempt_id
            and inventory.outcome == "found"
            and inventory.evidence == (evidence,)
            and inventory.provider_references
            == (getattr(binding, "provider_reference", None),)
            and getattr(binding, "eligible", False) is True
            and getattr(output, "output_asset_id", None)
            == getattr(binding, "output_asset_id", None)
            and getattr(output, "media_type", None) == "image/png"
            and asset.outcome == "found"
            and asset.media_type == "image/png"
            and isinstance(digest, str)
            and _evidence_sha256_matches(
                getattr(output, "output_content_hash", None), digest
            )
            and getattr(authorization, "attempt_id", None) == attempt_id
            and getattr(authorization, "provider_reference", None)
            == getattr(binding, "provider_reference", None)
            and getattr(authorization, "project_id", None)
            == getattr(binding, "project_id", None)
            and getattr(authorization, "page_id", None)
            == getattr(binding, "page_id", None)
            and getattr(authorization, "target_page_reference", None)
            == getattr(binding, "target_page_reference", None)
        )
        try:
            proof = ProviderGenerationPageOutputProof(
                project_id=getattr(binding, "project_id", ""),
                page_id=getattr(binding, "page_id", ""),
                target_page_reference=getattr(binding, "target_page_reference", ""),
                attempt_id=attempt_id,
                provenance_reference=getattr(evidence, "provenance_reference", ""),
                asset_id=getattr(binding, "output_asset_id", ""),
                content_sha256=digest if isinstance(digest, str) else "",
                provider_reference=getattr(binding, "provider_reference", ""),
            )
        except (TypeError, ValueError):
            return _BlockedProviderApplication()
        if not PageOutputApplicationAdmission().admit(
            proof, provider_proof_validated=valid
        ).allowed:
            return _BlockedProviderApplication()
        apply = getattr(self._delegate, "apply", None)
        if not callable(apply):
            return _BlockedProviderApplication()
        fence = self._fence_factory(self._claim.project_id, self._claim.page_id)
        original_fence_factory = getattr(self._delegate, "_fence_factory", None)
        if not callable(original_fence_factory):
            return _BlockedProviderApplication()
        delegate = cast(_FenceFactoryOwner, self._delegate)
        borrowed = _BorrowedPageFence(fence)

        def apply_under_shared_fence() -> object:
            delegate._fence_factory = lambda _project_id, _page_id: borrowed
            try:
                return apply(binding, authorization)
            finally:
                delegate._fence_factory = original_fence_factory

        observed = self._admission._observation_port.observe(
            self._claim.project_id, self._claim.page_id
        )
        if observed is not None and observed.page_state == "Generated":
            admitted, result = self._admission.run_generated_replay_admitted(
                self._claim,
                fence,
                getattr(binding, "output_asset_id", ""),
                apply_under_shared_fence,
            )
        else:
            admitted, result = self._admission.run_admitted(
                self._claim, fence, apply_under_shared_fence
            )
        if not admitted.admitted or result is None:
            return _BlockedProviderApplication()
        return result


def _replay_localfile_legacy_generated_application(
    repository: LocalFileRepository,
    attempt_id: str,
    authorized_by: str,
    authorized_at: datetime,
    application: _ProviderApplicationAdmission,
) -> bool:
    """Confirm one exact Generated replay and close its legacy attempt."""

    root = repository._next_generation_normal_execution_owner_root()
    attempts = LocalNormalExecutionAttemptStore(root / "attempts")
    record = attempts.lookup(attempt_id)
    observed = LocalWorkflowApplicationLedgerStore.observe_attempts(
        repository._workflow_application_ledger_owner_root(), (attempt_id,)
    )
    if (
        record is None
        or record.state not in {"PROVIDER_COMPLETED", "COMPLETED"}
        or observed.outcome != "found"
        or len(observed.bindings) != 1
    ):
        return False
    binding = observed.bindings[0]
    try:
        report = DurableEvidenceWorkflowBindingReport(
            attempt_id=binding.attempt_id,
            provider_reference=binding.provider_reference,
            output_asset_id=binding.output_asset_id,
            project_id=binding.project_id,
            page_id=binding.page_id,
            target_page_reference=binding.target_page_reference,
            status="eligible",
            eligible=True,
        )
        authorization = WorkflowApplicationAuthorizationDTO(
            authorization_id=binding.authorization_id,
            authorizer_id=authorized_by,
            authorized_at=authorized_at,
            attempt_id=binding.attempt_id,
            provider_reference=binding.provider_reference,
            project_id=binding.project_id,
            page_id=binding.page_id,
            target_page_reference=binding.target_page_reference,
            source_state="PromptBuilt",
            target_state="Generated",
        )
    except (TypeError, ValueError):
        return False
    result = application.apply(report, authorization)
    if getattr(result, "status", "") != "application_replay_confirmed":
        return False
    if record.state == "PROVIDER_COMPLETED":
        completed = attempts.complete_after_application(record.reservation)
        return completed.outcome in {"completed", "already_completed"}
    return record.completion_kind == "application_event_published"


def _observation_conflict(
    claim: PageGenerationModeClaim,
    observation: PageGenerationModeObservation | None,
) -> str | None:
    if observation is None:
        return "page_authority_missing"
    if (
        observation.project_id != claim.project_id
        or observation.page_id != claim.page_id
        or observation.page_revision != claim.page_revision
        or observation.page_fingerprint != claim.page_fingerprint
        or observation.page_state != claim.source_state
    ):
        return "page_authority_mismatch"
    return _mode_record_conflict(claim, observation)


def _generated_replay_conflict(
    claim: PageGenerationModeClaim,
    observation: PageGenerationModeObservation | None,
    expected_output_asset_id: str,
) -> str | None:
    if observation is None:
        return "page_authority_missing"
    if observation.page_state == claim.source_state:
        return "generated_replay_not_applicable"
    if (
        observation.project_id != claim.project_id
        or observation.page_id != claim.page_id
        or observation.page_state != "Generated"
    ):
        return "page_authority_mismatch"
    if (
        not isinstance(observation.output_asset_id, str)
        or not observation.output_asset_id
        or observation.output_asset_id != expected_output_asset_id
    ):
        return "generated_replay_output_asset_mismatch"
    return _mode_record_conflict(claim, observation)


def _mode_record_conflict(
    claim: PageGenerationModeClaim,
    observation: PageGenerationModeObservation,
) -> str | None:
    legacy = tuple(observation.legacy_record_references)
    panel = tuple(observation.panel_record_references)
    if len(set(legacy)) != len(legacy) or len(set(panel)) != len(panel):
        return "record_evidence_ambiguous"
    if legacy and panel:
        return "mixed_generation_modes"
    if claim.mode == "panel_aware":
        if legacy:
            return "legacy_mode_conflict"
        if panel and claim.mode_binding_reference not in panel:
            return "panel_record_mismatch"
    else:
        if panel:
            return "panel_mode_conflict"
        if legacy and claim.mode_binding_reference not in legacy:
            return "legacy_record_mismatch"
    return None
