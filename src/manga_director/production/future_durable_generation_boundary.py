"""Private, pre-provider durable admission core.

This module issues local permits and private one-shot dispatch requests only. It
has no provider edge, synthetic evidence, network operation, StateMachine
transition, or export.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import ConfigDict, Field, field_validator

from manga_director.production.director import DirectorModel
from manga_director.production.future_durable_generation_attempt import (
    FutureGenerationAttemptStoreResult,
    FutureGenerationAttemptV1,
    _LocalFutureGenerationAttemptStore,
)
from manga_director.production.future_generation_admission_contract import (
    GenerationAdmissionManifestV1,
    ProviderRequestBindingV1,
    content_digest,
)
from manga_director.production.future_generation_admission_evaluator import (
    GenerationAdmissionCurrentEvidence,
    GenerationAdmissionEvaluator,
)
from manga_director.workflow.page_execution_fence import PageExecutionFencePort

BoundaryEligibility = Literal["ELIGIBLE", "BLOCKED", "RECOVERY_REQUIRED"]


class CurrentAdmissionEvidenceReaderPort(Protocol):
    """Private seam used only by the isolated core and its focused tests."""

    def read(self, manifest: GenerationAdmissionManifestV1) -> GenerationAdmissionCurrentEvidence: ...


class _PermitModel(DirectorModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ProviderInvocationPermitV1(_PermitModel):
    """Redacted, non-reusable local capability for a future D06 adapter."""

    schema_id: Literal["manga_director.future_provider_invocation_permit"] = (
        "manga_director.future_provider_invocation_permit"
    )
    schema_version: Literal["1"] = "1"
    attempt_id: str
    project_id: str
    page_id: str
    execution_target_reference: str
    manifest_digest: str
    provider_binding_digest: str
    lifecycle: Literal["PROVIDER_STARTING"]
    sequence: int
    attempt_binding_digest: str

    @field_validator("attempt_id", "project_id", "page_id", "execution_target_reference")
    @classmethod
    def _logical_reference(cls, value: str) -> str:
        if not isinstance(value, str) or not value or value != value.strip() or any(char.isspace() for char in value):
            raise ValueError("provider permit requires logical references")
        if value.startswith(("/", "\\")) or "://" in value or (len(value) > 2 and value[1] == ":"):
            raise ValueError("provider permit must not contain paths or URLs")
        return value

    @field_validator("manifest_digest", "provider_binding_digest", "attempt_binding_digest")
    @classmethod
    def _digest(cls, value: str) -> str:
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("provider permit requires SHA-256 identities")
        return value


class ProviderDispatchRequestV1(_PermitModel):
    """Private one-shot D05 output for a future provider adapter boundary."""

    schema_id: Literal["manga_director.future_provider_dispatch_request"] = (
        "manga_director.future_provider_dispatch_request"
    )
    schema_version: Literal["1"] = "1"
    attempt_id: str
    project_id: str
    page_id: str
    execution_target_reference: str
    manifest_digest: str
    provider_binding_digest: str
    attempt_binding_digest: str
    consumption_sequence: int = Field(ge=0)
    dispatch_request_identity: str
    idempotency_identity: str
    provider_request: ProviderRequestBindingV1

    @field_validator("attempt_id", "project_id", "page_id", "execution_target_reference")
    @classmethod
    def _validate_dispatch_reference(cls, value: str) -> str:
        return ProviderInvocationPermitV1._logical_reference(value)

    @field_validator(
        "manifest_digest", "provider_binding_digest", "attempt_binding_digest", "dispatch_request_identity", "idempotency_identity"
    )
    @classmethod
    def _validate_dispatch_digest(cls, value: str) -> str:
        return ProviderInvocationPermitV1._digest(value)


@dataclass(frozen=True, slots=True)
class DurableGenerationBoundaryReport:
    eligibility: BoundaryEligibility
    code: str
    attempt: FutureGenerationAttemptV1 | None = None
    permit: ProviderInvocationPermitV1 | None = None


class _DurableGenerationBoundaryCore:
    """Injected test seam; trusted LocalFile composition never exposes it."""

    def __init__(
        self,
        store: _LocalFutureGenerationAttemptStore,
        current_evidence_reader: CurrentAdmissionEvidenceReaderPort,
        fence_factory: Callable[[str, str], PageExecutionFencePort],
    ) -> None:
        self._store = store
        self._reader = current_evidence_reader
        self._fence_factory = fence_factory
        self._evaluator = GenerationAdmissionEvaluator()

    def reserve(self, manifest: GenerationAdmissionManifestV1) -> DurableGenerationBoundaryReport:
        return _store_report(self._store.reserve(_new_attempt(manifest)), "RESERVATION")

    def prepare_provider_start(self, manifest: GenerationAdmissionManifestV1) -> DurableGenerationBoundaryReport:
        fence: PageExecutionFencePort | None = None
        try:
            fence = self._fence_factory(manifest.project_id, manifest.page_id)
            fence.acquire()
            current = self._store.lookup(manifest.attempt_id)
            expected = _new_attempt(manifest)
            if current.outcome != "confirmed" or current.attempt != expected:
                return _blocked("ATTEMPT_BINDING_UNAVAILABLE", current.attempt)
            fresh = self._reader.read(manifest)
            decision = self._evaluator.evaluate(manifest, fresh)
            if decision.status != "ADMITTED" or decision.manifest_digest != manifest.content_digest:
                return _blocked(f"FINAL_REVALIDATION_{decision.reason_code}", current.attempt)
            transitioned = self._store.transition(current.attempt, "PROVIDER_STARTING")
            if transitioned.outcome != "transitioned" or transitioned.attempt is None:
                return _blocked("PROVIDER_STARTING_PERSISTENCE_BLOCKED", transitioned.attempt)
            return DurableGenerationBoundaryReport(
                "ELIGIBLE",
                "FUTURE_PROVIDER_INVOCATION_PERMIT_ISSUED",
                transitioned.attempt,
                _permit(transitioned.attempt),
            )
        except Exception:
            return _blocked("FINAL_REVALIDATION_UNAVAILABLE")
        finally:
            if fence is not None:
                fence.release()

    def reopen(self, manifest: GenerationAdmissionManifestV1) -> DurableGenerationBoundaryReport:
        result = self._store.lookup(manifest.attempt_id)
        attempt = result.attempt
        if result.outcome == "corrupt":
            return _blocked("REOPEN_ATTEMPT_CORRUPT")
        if result.outcome != "confirmed" or attempt is None or not _same_binding(attempt, manifest):
            return _blocked("REOPEN_ATTEMPT_UNAVAILABLE", attempt)
        if attempt.lifecycle == "PROVIDER_STARTING":
            recovery = self._store.transition(attempt, "RECOVERY_REQUIRED")
            if recovery.outcome == "transitioned" and recovery.attempt is not None:
                return DurableGenerationBoundaryReport(
                    "RECOVERY_REQUIRED", "AMBIGUOUS_PROVIDER_START", recovery.attempt
                )
            return _blocked("AMBIGUOUS_PROVIDER_START_PERSISTENCE_UNAVAILABLE", recovery.attempt)
        if attempt.lifecycle == "RECOVERY_REQUIRED":
            return DurableGenerationBoundaryReport("RECOVERY_REQUIRED", "RECOVERY_REQUIRED", attempt)
        return _blocked(f"REOPEN_{attempt.lifecycle}", attempt)

    def permit_is_current(
        self, manifest: GenerationAdmissionManifestV1, permit: ProviderInvocationPermitV1
    ) -> bool:
        result = self._store.lookup(permit.attempt_id)
        return (
            result.outcome == "confirmed"
            and result.attempt is not None
            and result.attempt.lifecycle == "PROVIDER_STARTING"
            and result.attempt.dispatch_consumed_sequence is None
            and result.attempt.dispatch_request_identity is None
            and _same_binding(result.attempt, manifest)
            and permit == _permit(result.attempt)
        )

    def consume_for_dispatch(
        self, manifest: GenerationAdmissionManifestV1, permit: ProviderInvocationPermitV1
    ) -> ProviderDispatchRequestV1 | None:
        """Atomically consume a freshly revalidated local dispatch opportunity."""

        fence: PageExecutionFencePort | None = None
        try:
            fence = self._fence_factory(manifest.project_id, manifest.page_id)
            fence.acquire()
            current = self._store.lookup(manifest.attempt_id)
            if not _current_permit_matches(current, manifest, permit):
                return None
            fresh = self._reader.read(manifest)
            decision = self._evaluator.evaluate(manifest, fresh)
            if decision.status != "ADMITTED" or decision.manifest_digest != manifest.content_digest:
                return None
            attempt = current.attempt
            if attempt is None:
                return None
            identity = _dispatch_request_identity(attempt)
            consumed = self._store.consume(attempt, identity)
            if consumed.outcome != "consumed" or consumed.attempt is None:
                return None
            return _dispatch_request(consumed.attempt, manifest)
        except Exception:
            return None
        finally:
            if fence is not None:
                fence.release()


def _new_attempt(manifest: GenerationAdmissionManifestV1) -> FutureGenerationAttemptV1:
    return FutureGenerationAttemptV1(
        attempt_id=manifest.attempt_id,
        project_id=manifest.project_id,
        page_id=manifest.page_id,
        execution_target_reference=manifest.execution_target_reference,
        manifest_digest=manifest.content_digest,
        snapshot=manifest.snapshot,
        provider_binding_digest=content_digest(manifest.provider_request.canonical_projection()),
    )


def _permit(attempt: FutureGenerationAttemptV1) -> ProviderInvocationPermitV1:
    return ProviderInvocationPermitV1(
        attempt_id=attempt.attempt_id,
        project_id=attempt.project_id,
        page_id=attempt.page_id,
        execution_target_reference=attempt.execution_target_reference,
        manifest_digest=attempt.manifest_digest,
        provider_binding_digest=attempt.provider_binding_digest,
        lifecycle="PROVIDER_STARTING",
        sequence=attempt.sequence,
        attempt_binding_digest=attempt.binding_digest,
    )


def _same_binding(attempt: FutureGenerationAttemptV1, manifest: GenerationAdmissionManifestV1) -> bool:
    return attempt.binding_projection() == _new_attempt(manifest).binding_projection()


def _current_permit_matches(
    result: FutureGenerationAttemptStoreResult,
    manifest: GenerationAdmissionManifestV1,
    permit: ProviderInvocationPermitV1,
) -> bool:
    return (
        result.outcome == "confirmed"
        and result.attempt is not None
        and result.attempt.lifecycle == "PROVIDER_STARTING"
        and result.attempt.dispatch_consumed_sequence is None
        and result.attempt.dispatch_request_identity is None
        and _same_binding(result.attempt, manifest)
        and permit == _permit(result.attempt)
    )


def _dispatch_request_identity(attempt: FutureGenerationAttemptV1) -> str:
    return content_digest(
        {
            "attempt_binding_digest": attempt.binding_digest,
            "attempt_id": attempt.attempt_id,
            "execution_target_reference": attempt.execution_target_reference,
            "manifest_digest": attempt.manifest_digest,
            "page_id": attempt.page_id,
            "project_id": attempt.project_id,
            "provider_binding_digest": attempt.provider_binding_digest,
            "schema_id": "manga_director.future_provider_dispatch_request",
            "schema_version": "1",
            "sequence": attempt.sequence,
        }
    )


def _dispatch_request(
    attempt: FutureGenerationAttemptV1, manifest: GenerationAdmissionManifestV1
) -> ProviderDispatchRequestV1:
    if attempt.dispatch_consumed_sequence is None or attempt.dispatch_request_identity is None:
        raise ValueError("dispatch request requires consumed attempt")
    return ProviderDispatchRequestV1(
        attempt_id=attempt.attempt_id,
        project_id=attempt.project_id,
        page_id=attempt.page_id,
        execution_target_reference=attempt.execution_target_reference,
        manifest_digest=attempt.manifest_digest,
        provider_binding_digest=attempt.provider_binding_digest,
        attempt_binding_digest=attempt.binding_digest,
        consumption_sequence=attempt.dispatch_consumed_sequence,
        dispatch_request_identity=attempt.dispatch_request_identity,
        idempotency_identity=attempt.dispatch_request_identity,
        provider_request=manifest.provider_request,
    )


def _store_report(result: FutureGenerationAttemptStoreResult, prefix: str) -> DurableGenerationBoundaryReport:
    if result.outcome in {"reserved", "confirmed", "transitioned"} and result.attempt is not None:
        return DurableGenerationBoundaryReport("BLOCKED", f"{prefix}_{result.outcome.upper()}", result.attempt)
    return _blocked(f"{prefix}_{result.outcome.upper()}", result.attempt)


def _blocked(code: str, attempt: FutureGenerationAttemptV1 | None = None) -> DurableGenerationBoundaryReport:
    return DurableGenerationBoundaryReport("BLOCKED", code, attempt)
