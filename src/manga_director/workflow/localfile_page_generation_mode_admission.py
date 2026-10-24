"""Shared-fence admission for one private Page generation mode."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal, Protocol, TypeVar

from manga_director.production.next_generation_page_generation_mode_claim import (
    LocalPageGenerationModeClaimStore,
    PageGenerationModeClaim,
)
from manga_director.workflow.page_execution_fence import PageExecutionFencePort

_AdmittedActionResult = TypeVar("_AdmittedActionResult")


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


class PageGenerationModeObservationPort(Protocol):
    def observe(
        self, project_id: str, page_id: str
    ) -> PageGenerationModeObservation | None: ...


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
        action: Callable[[], bool],
    ) -> tuple[PageGenerationModeAdmissionResult, bool | None]:
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
