"""Internal validation of explicit provider output configuration for one attempt.

This preview boundary validates caller-supplied factual size and quality
configuration.  It neither chooses defaults nor invokes a provider.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Literal

from pydantic import ConfigDict, field_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_provider_configuration import (
    ProviderConfigurationNormalizationReport,
    ProviderConfigurationSelectionDTO,
)

FindingStatus = Literal["blocked"]
ReportStatus = Literal["ready", "blocked"]

_OPENAI_PROVIDER_ID = "openai"
_OPENAI_MODEL_ID = "gpt-image-2-2026-04-21"
_OUTPUT_QUALITIES = frozenset(("low", "medium", "high"))
_CANONICAL_SIZE = re.compile(r"^[1-9][0-9]*x[1-9][0-9]*$")
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


class _ProviderOutputConfigurationModel(DirectorModel):
    """Private base for closed, immutable internal-preview DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ProviderOutputConfigurationBindingDTO(_ProviderOutputConfigurationModel):
    """Explicit, provider-neutral output configuration for one exact attempt."""

    attempt_id: str
    provider_reference: str
    profile_id: str
    profile_version: str
    model_id: str
    output_size: str
    output_quality: str

    @field_validator(
        "attempt_id", "provider_reference", "profile_id", "profile_version", "model_id"
    )
    @classmethod
    def _validate_logical_reference(cls, value: str) -> str:
        return _logical_reference(value, "output configuration reference")


class ProviderOutputConfigurationFindingDTO(_ProviderOutputConfigurationModel):
    """One deterministic, redacted output-configuration finding."""

    code: str
    status: FindingStatus
    message: str
    attempt_id: str = ""
    provider_reference: str = ""
    profile_id: str = ""
    profile_version: str = ""
    model_id: str = ""

    @field_validator(
        "attempt_id", "provider_reference", "profile_id", "profile_version", "model_id"
    )
    @classmethod
    def _validate_optional_logical_reference(cls, value: str) -> str:
        return _logical_reference(value, "output configuration reference") if value else value


class ProviderOutputConfigurationBindingReport(_ProviderOutputConfigurationModel):
    """Canonical validation result without private provider runtime material."""

    provider_configuration_normalization_report: ProviderConfigurationNormalizationReport
    output_configuration: ProviderOutputConfigurationBindingDTO | None = None
    findings: tuple[ProviderOutputConfigurationFindingDTO, ...] = ()
    status: ReportStatus
    ready: bool
    analysis_only: Literal[True] = True


class ProviderOutputConfigurationBindingService:
    """Validate explicit output configuration without inference, I/O, or transport."""

    def validate(
        self,
        output_configuration: ProviderOutputConfigurationBindingDTO,
        provider_configuration_normalization_report: ProviderConfigurationNormalizationReport,
    ) -> ProviderOutputConfigurationBindingReport:
        """Return the canonical result for one caller-supplied configuration."""

        findings = _configuration_findings(output_configuration)
        selection = _ready_selection(provider_configuration_normalization_report)
        if selection is None:
            findings.append(_finding("PROVIDER_CONFIGURATION_NOT_READY"))
        else:
            findings.extend(_binding_findings(output_configuration, selection))
        return _report(
            provider_configuration_normalization_report,
            output_configuration,
            findings,
        )


def _ready_selection(
    report: ProviderConfigurationNormalizationReport,
) -> ProviderConfigurationSelectionDTO | None:
    if report.status != "ready" or report.ready is not True:
        return None
    return report.selection


def _configuration_findings(
    output_configuration: ProviderOutputConfigurationBindingDTO,
) -> list[ProviderOutputConfigurationFindingDTO]:
    findings = _size_findings(output_configuration)
    quality = output_configuration.output_quality
    if quality == "auto":
        findings.append(_finding("OUTPUT_QUALITY_AUTO_FORBIDDEN", output_configuration))
    elif quality not in _OUTPUT_QUALITIES:
        findings.append(_finding("OUTPUT_QUALITY_UNSUPPORTED", output_configuration))
    return findings


def _size_findings(
    output_configuration: ProviderOutputConfigurationBindingDTO,
) -> list[ProviderOutputConfigurationFindingDTO]:
    size = output_configuration.output_size
    if size == "auto":
        return [_finding("OUTPUT_SIZE_AUTO_FORBIDDEN", output_configuration)]
    if not _CANONICAL_SIZE.fullmatch(size):
        return [_finding("OUTPUT_SIZE_MALFORMED", output_configuration)]

    width_text, height_text = size.split("x")
    width, height = int(width_text), int(height_text)
    pixels = width * height
    if (
        width % 16 != 0
        or height % 16 != 0
        or width > 3840
        or height > 3840
        or max(width, height) > min(width, height) * 3
        or not 655_360 <= pixels <= 8_294_400
    ):
        return [_finding("OUTPUT_SIZE_UNSUPPORTED", output_configuration)]
    return []


def _binding_findings(
    output_configuration: ProviderOutputConfigurationBindingDTO,
    selection: ProviderConfigurationSelectionDTO,
) -> list[ProviderOutputConfigurationFindingDTO]:
    findings: list[ProviderOutputConfigurationFindingDTO] = []
    if output_configuration.attempt_id != selection.attempt_id:
        findings.append(_finding("ATTEMPT_BINDING_MISMATCH", output_configuration))
    if output_configuration.provider_reference != selection.provider_reference:
        findings.append(_finding("PROVIDER_BINDING_MISMATCH", output_configuration))
    if output_configuration.profile_id != selection.profile_id:
        findings.append(_finding("PROFILE_ID_BINDING_MISMATCH", output_configuration))
    if output_configuration.profile_version != selection.profile_version:
        findings.append(_finding("PROFILE_VERSION_BINDING_MISMATCH", output_configuration))
    if (
        selection.provider_id.availability != "known"
        or selection.provider_id.value != _OPENAI_PROVIDER_ID
    ):
        findings.append(_finding("OPENAI_PROVIDER_UNSUPPORTED", output_configuration))
    if (
        selection.model_id.availability != "known"
        or selection.model_id.value != _OPENAI_MODEL_ID
    ):
        findings.append(_finding("OPENAI_MODEL_UNSUPPORTED", output_configuration))
    if output_configuration.model_id != selection.model_id.value:
        findings.append(_finding("MODEL_BINDING_MISMATCH", output_configuration))
    return findings


def _report(
    upstream: ProviderConfigurationNormalizationReport,
    output_configuration: ProviderOutputConfigurationBindingDTO,
    findings: Iterable[ProviderOutputConfigurationFindingDTO],
) -> ProviderOutputConfigurationBindingReport:
    ordered = tuple(sorted(findings, key=_finding_key))
    ready = not ordered
    return ProviderOutputConfigurationBindingReport(
        provider_configuration_normalization_report=upstream,
        output_configuration=output_configuration if ready else None,
        findings=ordered,
        status="ready" if ready else "blocked",
        ready=ready,
    )


def _finding(
    code: str,
    output_configuration: ProviderOutputConfigurationBindingDTO | None = None,
) -> ProviderOutputConfigurationFindingDTO:
    return ProviderOutputConfigurationFindingDTO(
        code=code,
        status="blocked",
        message=code.replace("_", " ").lower(),
        attempt_id=_safe_value(output_configuration.attempt_id) if output_configuration else "",
        provider_reference=(
            _safe_value(output_configuration.provider_reference) if output_configuration else ""
        ),
        profile_id=_safe_value(output_configuration.profile_id) if output_configuration else "",
        profile_version=(
            _safe_value(output_configuration.profile_version) if output_configuration else ""
        ),
        model_id=_safe_value(output_configuration.model_id) if output_configuration else "",
    )


def _finding_key(
    item: ProviderOutputConfigurationFindingDTO,
) -> tuple[str, str, str, str, str, str, str]:
    return (
        item.code,
        item.status,
        item.attempt_id,
        item.provider_reference,
        item.profile_id,
        item.profile_version,
        item.model_id,
    )


def _logical_reference(value: str, label: str) -> str:
    if not _is_safe_string(value):
        raise ValueError(f"{label} must be a safe logical reference")
    return value


def _safe_value(value: str) -> str:
    return value if _is_safe_string(value) else ""


def _is_safe_string(value: str) -> bool:
    if not isinstance(value, str) or not value or value != value.strip() or any(char.isspace() for char in value):
        return False
    if value.startswith(("/", "\\")) or "://" in value or _WINDOWS_ABSOLUTE_PATH.match(value):
        return False
    return "@" not in value and not any(part in value.lower() for part in _SECRET_LIKE_PARTS)
