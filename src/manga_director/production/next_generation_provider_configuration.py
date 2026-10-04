"""Internal validation of factual provider configuration selected for one attempt.

This preview boundary accepts a composition-owned, caller-supplied snapshot.
It neither selects configuration nor accesses provider, credential, or storage
systems.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from pydantic import ConfigDict, ValidationError, field_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_authorized_execution_envelope import (
    AuthorizedGenerationExecutionEnvelopeDTO,
    AuthorizedGenerationExecutionEnvelopeValidationReport,
)
from manga_director.production.next_generation_generation_evidence import EvidenceValueDTO

FindingStatus = Literal["blocked"]
ReportStatus = Literal["ready", "blocked"]

_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")
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


class _ProviderConfigurationModel(DirectorModel):
    """Private base for closed, immutable internal-preview DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ProviderConfigurationSelectionDTO(_ProviderConfigurationModel):
    """Redacted factual configuration selected for one exact attempt."""

    attempt_id: str
    provider_reference: str
    profile_id: str
    profile_version: str
    provider_id: EvidenceValueDTO
    model_id: EvidenceValueDTO
    model_version: EvidenceValueDTO
    workflow_id: EvidenceValueDTO
    workflow_version: EvidenceValueDTO
    preset_id: EvidenceValueDTO | None = None
    preset_version: EvidenceValueDTO | None = None
    requested_seed: EvidenceValueDTO | None = None

    @field_validator("attempt_id", "provider_reference", "profile_id", "profile_version")
    @classmethod
    def _validate_logical_reference(cls, value: str) -> str:
        return _logical_reference(value, "configuration reference")

    @field_validator(
        "provider_id",
        "model_id",
        "model_version",
        "workflow_id",
        "workflow_version",
        "preset_id",
        "preset_version",
    )
    @classmethod
    def _validate_identity_evidence(cls, value: EvidenceValueDTO | None) -> EvidenceValueDTO | None:
        if value is not None and value.availability == "known":
            if not isinstance(value.value, str):
                raise ValueError("known configuration identity evidence must be a string")
            _logical_reference(value.value, "configuration identity")
        return value

    @field_validator("requested_seed")
    @classmethod
    def _validate_requested_seed(cls, value: EvidenceValueDTO | None) -> EvidenceValueDTO | None:
        if value is not None and isinstance(value.value, str):
            _safe_seed_string(value.value)
        return value


class ProviderConfigurationNormalizationFindingDTO(_ProviderConfigurationModel):
    """One deterministic redacted configuration-normalization finding."""

    code: str
    status: FindingStatus
    message: str
    attempt_id: str = ""
    provider_reference: str = ""
    profile_id: str = ""
    profile_version: str = ""

    @field_validator("attempt_id", "provider_reference", "profile_id", "profile_version")
    @classmethod
    def _validate_optional_logical_reference(cls, value: str) -> str:
        return _logical_reference(value, "configuration reference") if value else value


class ProviderConfigurationNormalizationReport(_ProviderConfigurationModel):
    """Canonical validation result with no runtime configuration material."""

    authorized_execution_envelope_validation_report: (
        AuthorizedGenerationExecutionEnvelopeValidationReport
    )
    selection: ProviderConfigurationSelectionDTO | None = None
    findings: tuple[ProviderConfigurationNormalizationFindingDTO, ...] = ()
    status: ReportStatus
    ready: bool
    analysis_only: Literal[True] = True


@dataclass(frozen=True, slots=True)
class AuthoritativeProviderConfigurationSnapshot:
    """Composition-owned factual selection input with no credentials or payload."""

    attempt_id: str
    provider_reference: str
    profile_id: str
    profile_version: str
    provider_id: EvidenceValueDTO
    model_id: EvidenceValueDTO
    model_version: EvidenceValueDTO
    workflow_id: EvidenceValueDTO
    workflow_version: EvidenceValueDTO
    preset_id: EvidenceValueDTO | None = None
    preset_version: EvidenceValueDTO | None = None
    requested_seed: EvidenceValueDTO | None = None


class ProviderConfigurationNormalizationService:
    """Validate exactly bound factual configuration without inference or I/O."""

    def normalize(
        self,
        attempt_id: str,
        snapshot: AuthoritativeProviderConfigurationSnapshot,
        authorized_execution_envelope_validation_report: (
            AuthorizedGenerationExecutionEnvelopeValidationReport
        ),
    ) -> ProviderConfigurationNormalizationReport:
        """Return a canonical projection of a caller-supplied factual selection."""

        report = authorized_execution_envelope_validation_report
        if not _is_logical_reference(attempt_id):
            return _report(report, None, [_finding("INVALID_LOGICAL_REFERENCE")])
        selection = _selection(snapshot)
        if selection is None:
            return _report(report, None, [_finding("UNSAFE_CONFIGURATION_EVIDENCE", attempt_id)])

        findings = _upstream_findings(report)
        envelopes = tuple(item for item in report.envelopes if item.attempt_id == attempt_id)
        if not findings:
            if not envelopes:
                findings.append(_finding("AUTHORIZED_ATTEMPT_NOT_FOUND", attempt_id))
            elif len(envelopes) > 1:
                findings.append(_finding("AUTHORIZED_ATTEMPT_NOT_UNIQUE", attempt_id))
        if len(envelopes) == 1:
            findings.extend(_binding_findings(attempt_id, selection, report, envelopes[0]))
        ordered = tuple(sorted(findings, key=_finding_key))
        return _report(report, selection if not ordered else None, ordered)


def _selection(
    snapshot: AuthoritativeProviderConfigurationSnapshot,
) -> ProviderConfigurationSelectionDTO | None:
    try:
        return ProviderConfigurationSelectionDTO(
            attempt_id=snapshot.attempt_id,
            provider_reference=snapshot.provider_reference,
            profile_id=snapshot.profile_id,
            profile_version=snapshot.profile_version,
            provider_id=snapshot.provider_id,
            model_id=snapshot.model_id,
            model_version=snapshot.model_version,
            workflow_id=snapshot.workflow_id,
            workflow_version=snapshot.workflow_version,
            preset_id=snapshot.preset_id,
            preset_version=snapshot.preset_version,
            requested_seed=snapshot.requested_seed,
        )
    except (TypeError, ValidationError, ValueError):
        return None


def _upstream_findings(
    report: AuthorizedGenerationExecutionEnvelopeValidationReport,
) -> list[ProviderConfigurationNormalizationFindingDTO]:
    if report.status == "ready" and report.ready is True:
        return []
    return [_finding("AUTHORIZED_ENVELOPE_NOT_READY")]


def _binding_findings(
    attempt_id: str,
    selection: ProviderConfigurationSelectionDTO,
    report: AuthorizedGenerationExecutionEnvelopeValidationReport,
    envelope: AuthorizedGenerationExecutionEnvelopeDTO,
) -> list[ProviderConfigurationNormalizationFindingDTO]:
    request = (
        report.execution_authorization_validation_report.readiness_report.input.request_validation_report.request
    )
    findings: list[ProviderConfigurationNormalizationFindingDTO] = []
    if selection.attempt_id != attempt_id or envelope.attempt_id != attempt_id:
        findings.append(_finding("ATTEMPT_BINDING_MISMATCH", attempt_id))
    if selection.provider_reference != envelope.provider_reference:
        findings.append(
            _finding(
                "PROVIDER_REFERENCE_MISMATCH",
                attempt_id,
                selection.provider_reference,
                selection.profile_id,
                selection.profile_version,
            )
        )
    if selection.profile_id != envelope.profile_id or selection.profile_id != request.profile_id:
        findings.append(
            _finding(
                "PROFILE_ID_MISMATCH",
                attempt_id,
                selection.provider_reference,
                selection.profile_id,
                selection.profile_version,
            )
        )
    if (
        selection.profile_version != envelope.profile_version
        or selection.profile_version != request.profile_version
    ):
        findings.append(
            _finding(
                "PROFILE_VERSION_MISMATCH",
                attempt_id,
                selection.provider_reference,
                selection.profile_id,
                selection.profile_version,
            )
        )
    return findings


def _report(
    upstream: AuthorizedGenerationExecutionEnvelopeValidationReport,
    selection: ProviderConfigurationSelectionDTO | None,
    findings: Iterable[ProviderConfigurationNormalizationFindingDTO],
) -> ProviderConfigurationNormalizationReport:
    ordered = tuple(sorted(findings, key=_finding_key))
    ready = not ordered and selection is not None
    return ProviderConfigurationNormalizationReport(
        authorized_execution_envelope_validation_report=upstream,
        selection=selection if ready else None,
        findings=ordered,
        status="ready" if ready else "blocked",
        ready=ready,
    )


def _finding(
    code: str,
    attempt_id: str = "",
    provider_reference: str = "",
    profile_id: str = "",
    profile_version: str = "",
) -> ProviderConfigurationNormalizationFindingDTO:
    return ProviderConfigurationNormalizationFindingDTO(
        code=code,
        status="blocked",
        message=code.replace("_", " ").lower(),
        attempt_id=_safe_value(attempt_id),
        provider_reference=_safe_value(provider_reference),
        profile_id=_safe_value(profile_id),
        profile_version=_safe_value(profile_version),
    )


def _finding_key(
    item: ProviderConfigurationNormalizationFindingDTO,
) -> tuple[str, str, str, str, str, str]:
    return (
        item.code,
        item.status,
        item.attempt_id,
        item.provider_reference,
        item.profile_id,
        item.profile_version,
    )


def _safe_seed_string(value: str) -> str:
    if not _is_safe_string(value):
        raise ValueError("requested seed string is not allowed")
    return value


def _logical_reference(value: str, label: str) -> str:
    if not _is_logical_reference(value):
        raise ValueError(f"{label} must be a safe logical reference")
    return value


def _safe_value(value: str) -> str:
    return value if _is_logical_reference(value) else ""


def _is_logical_reference(value: str) -> bool:
    return _is_safe_string(value)


def _is_safe_string(value: str) -> bool:
    if not isinstance(value, str) or not value or value != value.strip() or any(char.isspace() for char in value):
        return False
    if value.startswith(("/", "\\")) or "://" in value or _WINDOWS_ABSOLUTE_PATH.match(value):
        return False
    if "@" in value or any(part in value.lower() for part in _SECRET_LIKE_PARTS):
        return False
    return True
