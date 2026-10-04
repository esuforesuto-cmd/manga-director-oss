"""Internal composition of one exact-bound provider invocation adapter.

This preview boundary creates a short-lived implementation of the frozen
provider invocation port.  Provider-private request, response, prompt, and
opaque backing material remain runtime-only and never enter durable reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

from manga_director.production.next_generation_provider_configuration import (
    ProviderConfigurationNormalizationReport,
    ProviderConfigurationSelectionDTO,
)
from manga_director.production.next_generation_provider_invocation import (
    OpaqueGeneratedOutputHandle,
    OpenAIFailureDiagnosticCategory,
    ProviderGenerationInvocationPort,
    ProviderInvocationRuntimeResult,
)
from manga_director.production.next_generation_secure_execution_input_resolution import (
    MaterializedGenerationInput,
    OpaqueReferenceAssetHandle,
)

PrivateTransportOutcome = Literal["succeeded", "provider_failed", "runtime_failed"]


@dataclass(frozen=True, slots=True)
class ProviderPrivateTransportRequest:
    """One provider-private request; do not serialize or persist this value."""

    attempt_id: str
    provider_reference: str
    profile_id: str
    profile_version: str
    configuration_selection: ProviderConfigurationSelectionDTO
    raw_prompt: str = field(repr=False, compare=False)
    reference_asset_handles: tuple[OpaqueReferenceAssetHandle, ...] = field(
        repr=False, compare=False, default=()
    )


@dataclass(frozen=True, slots=True)
class ProviderPrivateTransportResult:
    """Provider-private result with no reportable provider detail."""

    outcome: PrivateTransportOutcome
    output_material: object | None = field(repr=False, compare=False, default=None)
    diagnostic_category: OpenAIFailureDiagnosticCategory | None = None


class ProviderPrivateTransportPort(Protocol):
    """Provider-specific private transport invoked once by a bound adapter."""

    def invoke(
        self, request: ProviderPrivateTransportRequest
    ) -> ProviderPrivateTransportResult: ...


class BoundProviderGenerationInvocationAdapter(ProviderGenerationInvocationPort):
    """Short-lived port implementation bound to one immutable selection."""

    def __init__(
        self,
        selection: ProviderConfigurationSelectionDTO,
        private_transport: ProviderPrivateTransportPort,
    ) -> None:
        self._selection = selection
        self._private_transport = private_transport

    @property
    def provider_reference(self) -> str:
        return str(self._selection.provider_reference)

    def invoke(self, materialized_input: MaterializedGenerationInput) -> ProviderInvocationRuntimeResult:
        """Invoke private transport once only after exact binding validation."""

        if not _matches_selection(materialized_input, self._selection):
            return _runtime_failure(materialized_input.attempt_id, self.provider_reference)

        request = ProviderPrivateTransportRequest(
            attempt_id=materialized_input.attempt_id,
            provider_reference=materialized_input.provider_reference,
            profile_id=materialized_input.profile_id,
            profile_version=materialized_input.profile_version,
            configuration_selection=self._selection,
            raw_prompt=materialized_input.raw_prompt,
            reference_asset_handles=materialized_input.reference_asset_handles,
        )
        try:
            result = self._private_transport.invoke(request)
        except Exception:
            return _runtime_failure(materialized_input.attempt_id, self.provider_reference)
        return _normalize_private_result(result, materialized_input.attempt_id, self.provider_reference)


class ProviderAdapterCompositionService:
    """Create one internal adapter only from a ready normalized selection."""

    def compose(
        self,
        configuration_normalization_report: ProviderConfigurationNormalizationReport,
        private_transport: ProviderPrivateTransportPort,
    ) -> BoundProviderGenerationInvocationAdapter | None:
        """Fail closed when configuration evidence is not ready for invocation."""

        if (
            configuration_normalization_report.status != "ready"
            or configuration_normalization_report.ready is not True
            or configuration_normalization_report.selection is None
        ):
            return None
        return BoundProviderGenerationInvocationAdapter(
            configuration_normalization_report.selection,
            private_transport,
        )


def _matches_selection(
    materialized_input: MaterializedGenerationInput,
    selection: ProviderConfigurationSelectionDTO,
) -> bool:
    return bool(
        materialized_input.attempt_id == selection.attempt_id
        and materialized_input.provider_reference == selection.provider_reference
        and materialized_input.profile_id == selection.profile_id
        and materialized_input.profile_version == selection.profile_version
    )


def _normalize_private_result(
    result: object,
    attempt_id: str,
    provider_reference: str,
) -> ProviderInvocationRuntimeResult:
    if not isinstance(result, ProviderPrivateTransportResult):
        return _runtime_failure(attempt_id, provider_reference)
    if result.outcome == "succeeded":
        if result.output_material is None:
            return _runtime_failure(attempt_id, provider_reference)
        return ProviderInvocationRuntimeResult(
            attempt_id=attempt_id,
            provider_reference=provider_reference,
            outcome="succeeded",
            output_handle=OpaqueGeneratedOutputHandle(result.output_material),
        )
    if result.outcome == "provider_failed" and result.output_material is None:
        if result.diagnostic_category not in (None, "provider_declared_failure"):
            return _runtime_failure(attempt_id, provider_reference)
        return ProviderInvocationRuntimeResult(
            attempt_id=attempt_id,
            provider_reference=provider_reference,
            outcome="provider_failed",
            failure_category="provider_declared_failure",
            diagnostic_category=result.diagnostic_category,
        )
    if result.outcome == "runtime_failed" and result.output_material is None:
        if result.diagnostic_category == "provider_declared_failure":
            return _runtime_failure(attempt_id, provider_reference)
        return _runtime_failure(attempt_id, provider_reference, result.diagnostic_category)
    return _runtime_failure(attempt_id, provider_reference)


def _runtime_failure(
    attempt_id: str,
    provider_reference: str = "",
    diagnostic_category: OpenAIFailureDiagnosticCategory | None = None,
) -> ProviderInvocationRuntimeResult:
    return ProviderInvocationRuntimeResult(
        attempt_id=attempt_id,
        provider_reference=provider_reference,
        outcome="runtime_failed",
        failure_category="runtime_failure",
        diagnostic_category=diagnostic_category,
    )
