"""Internal secure resolution of one authorized generation input.

This preview boundary binds supplied logical evidence to a short-lived runtime
input.  It does not invoke a provider, persist material, or retain raw prompt
content in a DTO or report.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Literal, Protocol

from pydantic import ConfigDict, field_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_authorized_execution_envelope import (
    AuthorizedGenerationExecutionEnvelopeDTO,
    AuthorizedGenerationExecutionEnvelopeValidationReport,
)

FindingStatus = Literal["needs_review", "blocked"]
ReportStatus = Literal["ready", "needs_review", "blocked"]

_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\\\/]")
_SECRET_LIKE_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "endpoint",
    "password",
    "secret",
    "token",
)


class _SecureInputResolutionModel(DirectorModel):
    """Private base for closed, immutable internal-preview DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class SecureExecutionInputResolutionFindingDTO(_SecureInputResolutionModel):
    """One deterministic, redacted input-resolution finding."""

    code: str
    status: FindingStatus
    message: str
    attempt_id: str = ""
    input_reference: str = ""
    generation_intent_reference: str = ""
    reference_asset_id: str = ""


class SecureExecutionInputResolutionReport(_SecureInputResolutionModel):
    """A raw-prompt-free report for one explicit execution attempt."""

    authorized_execution_envelope_validation_report: (
        AuthorizedGenerationExecutionEnvelopeValidationReport
    )
    attempt_id: str
    findings: tuple[SecureExecutionInputResolutionFindingDTO, ...] = ()
    status: ReportStatus
    ready: bool
    input_materialized: bool
    reference_assets_resolved: bool

    @field_validator("attempt_id")
    @classmethod
    def _validate_attempt_id(cls, value: str) -> str:
        return _logical_reference(value)


@dataclass(frozen=True, slots=True)
class AuthoritativeExecutionInputSnapshot:
    """Resolver-owned snapshot with no public raw-prompt field."""

    input_reference: str
    generation_intent_reference: str
    required_reference_asset_ids: tuple[str, ...] = ()
    prompt_materializer: Callable[[], object] = field(
        repr=False, compare=False, default=lambda: ""
    )

    @classmethod
    def from_prompt_material(
        cls,
        *,
        input_reference: str,
        generation_intent_reference: str,
        raw_prompt_material: object,
        required_reference_asset_ids: tuple[str, ...] = (),
    ) -> AuthoritativeExecutionInputSnapshot:
        """Create an in-memory snapshot without exposing prompt as a field."""

        return cls(
            input_reference=input_reference,
            generation_intent_reference=generation_intent_reference,
            required_reference_asset_ids=required_reference_asset_ids,
            prompt_materializer=lambda: raw_prompt_material,
        )

    def materialize_prompt(self) -> str:
        """Return prompt material only to the enclosing resolution operation."""

        prompt = self.prompt_materializer()
        if not isinstance(prompt, str) or not prompt:
            raise ValueError("prompt material is unavailable")
        return prompt


@dataclass(frozen=True, slots=True)
class OpaqueReferenceAssetHandle:
    """A read-only runtime handle whose backing content stays outside core."""

    reference_asset_id: str
    opaque_value: object = field(repr=False, compare=False, default=None)


@dataclass(frozen=True, slots=True)
class MaterializedGenerationInput:
    """Private runtime handoff; never use this type as a DTO or evidence model."""

    attempt_id: str
    request_id: str
    provider_reference: str
    profile_id: str
    profile_version: str
    generation_intent_reference: str
    input_reference: str
    raw_prompt: str = field(repr=False, compare=False)
    reference_asset_handles: tuple[OpaqueReferenceAssetHandle, ...] = ()


@dataclass(frozen=True, slots=True)
class SecureExecutionInputResolutionOutcome:
    """Private operation outcome that keeps runtime material out of reports."""

    report: SecureExecutionInputResolutionReport
    materialized_input: MaterializedGenerationInput | None = field(repr=False, default=None)


class GenerationInputResolverPort(Protocol):
    """Resolve one logical input reference without exposing storage details."""

    def resolve(self, input_reference: str) -> AuthoritativeExecutionInputSnapshot | None: ...


class ReferenceAssetResolverPort(Protocol):
    """Resolve one approved logical asset reference into an opaque handle."""

    def resolve(self, reference_asset_id: str) -> OpaqueReferenceAssetHandle | None: ...


class SecureExecutionInputResolutionService:
    """Materialize one authorized input without provider, workflow, or I/O behavior."""

    def resolve(
        self,
        attempt_id: str,
        authorized_execution_envelope_validation_report: (
            AuthorizedGenerationExecutionEnvelopeValidationReport
        ),
        generation_input_resolver: GenerationInputResolverPort,
        reference_asset_resolver: ReferenceAssetResolverPort,
    ) -> SecureExecutionInputResolutionOutcome:
        """Resolve one explicit attempt using supplied read-only resolver ports."""

        findings = _upstream_findings(
            attempt_id, authorized_execution_envelope_validation_report
        )
        envelope = _matching_envelope(
            attempt_id, authorized_execution_envelope_validation_report
        )
        if not findings and envelope is None:
            findings.append(
                _finding("EXECUTION_ATTEMPT_NOT_FOUND", "blocked", attempt_id=attempt_id)
            )
        if findings or envelope is None:
            return _outcome(
                authorized_execution_envelope_validation_report,
                attempt_id,
                findings,
                reference_assets_resolved=False,
            )

        snapshot = _resolve_snapshot(generation_input_resolver, envelope, findings)
        if snapshot is None:
            return _outcome(
                authorized_execution_envelope_validation_report,
                attempt_id,
                findings,
                reference_assets_resolved=False,
            )

        expected_asset_ids = _expected_reference_asset_ids(
            authorized_execution_envelope_validation_report
        )
        actual_asset_ids = tuple(sorted(snapshot.required_reference_asset_ids))
        for asset_id in _duplicates(snapshot.required_reference_asset_ids):
            findings.append(
                _finding(
                    "DUPLICATE_REQUIRED_REFERENCE_ASSET_ID",
                    "blocked",
                    envelope,
                    reference_asset_id=asset_id,
                )
            )
        if actual_asset_ids != expected_asset_ids:
            findings.append(
                _finding("REQUIRED_REFERENCE_ASSET_SET_MISMATCH", "blocked", envelope)
            )
        if findings:
            return _outcome(
                authorized_execution_envelope_validation_report,
                attempt_id,
                findings,
                reference_assets_resolved=False,
            )

        handles = _resolve_reference_assets(
            reference_asset_resolver, envelope, expected_asset_ids, findings
        )
        if findings:
            return _outcome(
                authorized_execution_envelope_validation_report,
                attempt_id,
                findings,
                reference_assets_resolved=False,
            )

        prompt = _materialize_prompt(snapshot, envelope, findings)
        if prompt is None:
            return _outcome(
                authorized_execution_envelope_validation_report,
                attempt_id,
                findings,
                reference_assets_resolved=True,
            )

        materialized = MaterializedGenerationInput(
            attempt_id=envelope.attempt_id,
            request_id=envelope.request_id,
            provider_reference=envelope.provider_reference,
            profile_id=envelope.profile_id,
            profile_version=envelope.profile_version,
            generation_intent_reference=envelope.generation_intent_reference,
            input_reference=envelope.input_reference,
            raw_prompt=prompt,
            reference_asset_handles=handles,
        )
        return _outcome(
            authorized_execution_envelope_validation_report,
            attempt_id,
            findings,
            materialized_input=materialized,
            reference_assets_resolved=True,
        )


def _upstream_findings(
    attempt_id: str,
    report: AuthorizedGenerationExecutionEnvelopeValidationReport,
) -> list[SecureExecutionInputResolutionFindingDTO]:
    if report.status == "ready" and report.ready is True:
        return []
    if report.status == "needs_review" and report.ready is False:
        return [
            _finding(
                "AUTHORIZED_EXECUTION_ENVELOPE_NEEDS_REVIEW",
                "needs_review",
                attempt_id=attempt_id,
            )
        ]
    return [_finding("AUTHORIZED_EXECUTION_ENVELOPE_BLOCKED", "blocked", attempt_id=attempt_id)]


def _matching_envelope(
    attempt_id: str,
    report: AuthorizedGenerationExecutionEnvelopeValidationReport,
) -> AuthorizedGenerationExecutionEnvelopeDTO | None:
    matches = tuple(envelope for envelope in report.envelopes if envelope.attempt_id == attempt_id)
    return matches[0] if len(matches) == 1 else None


def _resolve_snapshot(
    resolver: GenerationInputResolverPort,
    envelope: AuthorizedGenerationExecutionEnvelopeDTO,
    findings: list[SecureExecutionInputResolutionFindingDTO],
) -> AuthoritativeExecutionInputSnapshot | None:
    try:
        snapshot = resolver.resolve(envelope.input_reference)
    except Exception:
        snapshot = None
    if snapshot is None or snapshot.input_reference != envelope.input_reference:
        findings.append(_finding("INPUT_REFERENCE_UNRESOLVABLE", "blocked", envelope))
        return None
    if snapshot.generation_intent_reference != envelope.generation_intent_reference:
        findings.append(_finding("GENERATION_INTENT_BINDING_MISMATCH", "blocked", envelope))
        return None
    return snapshot


def _expected_reference_asset_ids(
    report: AuthorizedGenerationExecutionEnvelopeValidationReport,
) -> tuple[str, ...]:
    request = (
        report.execution_authorization_validation_report.readiness_report.input.request_validation_report.request
    )
    return tuple(
        sorted(
            {
                asset_id
                for binding in request.identity_bindings
                for asset_id in binding.reference_asset_ids
            }
        )
    )


def _resolve_reference_assets(
    resolver: ReferenceAssetResolverPort,
    envelope: AuthorizedGenerationExecutionEnvelopeDTO,
    asset_ids: tuple[str, ...],
    findings: list[SecureExecutionInputResolutionFindingDTO],
) -> tuple[OpaqueReferenceAssetHandle, ...]:
    handles: list[OpaqueReferenceAssetHandle] = []
    for asset_id in asset_ids:
        try:
            handle = resolver.resolve(asset_id)
        except Exception:
            handle = None
        if handle is None or handle.reference_asset_id != asset_id:
            findings.append(
                _finding(
                    "REQUIRED_REFERENCE_ASSET_UNRESOLVABLE",
                    "blocked",
                    envelope,
                    reference_asset_id=asset_id,
                )
            )
            continue
        handles.append(handle)
    return tuple(handles)


def _materialize_prompt(
    snapshot: AuthoritativeExecutionInputSnapshot,
    envelope: AuthorizedGenerationExecutionEnvelopeDTO,
    findings: list[SecureExecutionInputResolutionFindingDTO],
) -> str | None:
    try:
        prompt = snapshot.materialize_prompt()
    except Exception:
        findings.append(_finding("PROMPT_MATERIALIZATION_FAILED", "blocked", envelope))
        return None
    if not prompt.strip():
        findings.append(_finding("PROMPT_MATERIALIZATION_FAILED", "blocked", envelope))
        return None
    return prompt


def _outcome(
    report: AuthorizedGenerationExecutionEnvelopeValidationReport,
    attempt_id: str,
    findings: Iterable[SecureExecutionInputResolutionFindingDTO],
    *,
    materialized_input: MaterializedGenerationInput | None = None,
    reference_assets_resolved: bool,
) -> SecureExecutionInputResolutionOutcome:
    ordered_findings = tuple(sorted(findings, key=_finding_key))
    status = _report_status(ordered_findings)
    resolution_report = SecureExecutionInputResolutionReport(
        authorized_execution_envelope_validation_report=report,
        attempt_id=attempt_id,
        findings=ordered_findings,
        status=status,
        ready=status == "ready",
        input_materialized=materialized_input is not None,
        reference_assets_resolved=reference_assets_resolved,
    )
    return SecureExecutionInputResolutionOutcome(
        report=resolution_report,
        materialized_input=materialized_input,
    )


def _finding(
    code: str,
    status: FindingStatus,
    envelope: AuthorizedGenerationExecutionEnvelopeDTO | None = None,
    *,
    attempt_id: str = "",
    reference_asset_id: str = "",
) -> SecureExecutionInputResolutionFindingDTO:
    return SecureExecutionInputResolutionFindingDTO(
        code=code,
        status=status,
        message=code.replace("_", " ").lower(),
        attempt_id=envelope.attempt_id if envelope is not None else attempt_id,
        input_reference=envelope.input_reference if envelope is not None else "",
        generation_intent_reference=(
            envelope.generation_intent_reference if envelope is not None else ""
        ),
        reference_asset_id=reference_asset_id,
    )


def _duplicates(values: Iterable[str]) -> tuple[str, ...]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return tuple(sorted(value for value, count in counts.items() if count > 1))


def _finding_key(
    item: SecureExecutionInputResolutionFindingDTO,
) -> tuple[str, str, str, str, str, str]:
    return (
        item.code,
        item.status,
        item.attempt_id,
        item.input_reference,
        item.generation_intent_reference,
        item.reference_asset_id,
    )


def _report_status(
    findings: tuple[SecureExecutionInputResolutionFindingDTO, ...],
) -> ReportStatus:
    if any(item.status == "blocked" for item in findings):
        return "blocked"
    if any(item.status == "needs_review" for item in findings):
        return "needs_review"
    return "ready"


def _logical_reference(value: str) -> str:
    if not value or value != value.strip() or any(character.isspace() for character in value):
        raise ValueError("attempt_id must be a nonblank logical reference")
    if value.startswith(("/", "\\")) or "://" in value or _WINDOWS_ABSOLUTE_PATH.match(value):
        raise ValueError("attempt_id must not be a path or URL")
    if "@" in value or any(part in value.lower() for part in _SECRET_LIKE_PARTS):
        raise ValueError("attempt_id must not contain private material")
    return value
