"""Internal, prompt-only OpenAI Image API private transport.

This adapter consumes only the already exact-bound private transport request.
It intentionally retains prompt, credential, SDK response, and decoded image
material only in short-lived runtime objects.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass, field
from typing import Protocol

from manga_director.production.next_generation_provider_adapter_composition import (
    ProviderPrivateTransportRequest,
    ProviderPrivateTransportResult,
)
from manga_director.production.next_generation_provider_invocation import (
    OpenAIFailureDiagnosticCategory,
)
from manga_director.production.next_generation_provider_output_configuration import (
    ProviderOutputConfigurationBindingDTO,
    ProviderOutputConfigurationBindingReport,
    ProviderOutputConfigurationBindingService,
)

_OPENAI_PROVIDER_ID = "openai"
_OPENAI_MODEL_ID = "gpt-image-2-2026-04-21"
_TIMEOUT_SECONDS = 120
_MAX_RETRIES = 0
_IMAGE_COUNT = 1
_MAX_DECODED_OUTPUT_BYTES = 25 * 1024 * 1024
_MAX_BASE64_CHARS = 4 * ((_MAX_DECODED_OUTPUT_BYTES + 2) // 3)


class OpenAIPrivateCredentialResolverPort(Protocol):
    """Resolve one private credential immediately before a provider call."""

    def resolve(self) -> str: ...


class OpenAIImageClientPort(Protocol):
    """Minimal private SDK client surface used by this adapter."""

    def generate_image(
        self,
        *,
        model: str,
        prompt: str,
        n: int,
        size: str,
        quality: str,
    ) -> object: ...

    def close(self) -> None: ...


class OpenAIImageClientFactoryPort(Protocol):
    """Create a private OpenAI SDK client without exposing credentials outward."""

    def create(
        self,
        credential: str,
        *,
        timeout_seconds: int,
        max_retries: int,
    ) -> OpenAIImageClientPort: ...


@dataclass(frozen=True, slots=True)
class OpenAIInMemoryGeneratedImageMaterial:
    """Private decoded image material; this is carried only by an opaque handle."""

    image_bytes: bytes = field(repr=False, compare=False)
    media_type: str = "image/png"


class OpenAIImageSdkClientFactory:
    """SDK-backed private factory; it performs no request during construction."""

    def create(
        self,
        credential: str,
        *,
        timeout_seconds: int,
        max_retries: int,
    ) -> OpenAIImageClientPort:
        """Create an SDK client with the frozen private transport controls."""

        from openai import OpenAI

        return _OpenAIImageSdkClient(
            OpenAI(api_key=credential, timeout=timeout_seconds, max_retries=max_retries)
        )


class _OpenAIImageSdkClient:
    """Private wrapper that prevents SDK response objects leaving this module."""

    def __init__(self, client: object) -> None:
        self._client = client

    def generate_image(
        self,
        *,
        model: str,
        prompt: str,
        n: int,
        size: str,
        quality: str,
    ) -> object:
        return self._client.images.generate(  # type: ignore[attr-defined]
            model=model,
            prompt=prompt,
            n=n,
            size=size,
            quality=quality,
        )

    def close(self) -> None:
        self._client.close()  # type: ignore[attr-defined]


class OpenAIImagePrivateTransport:
    """OpenAI transport with captured explicit output configuration and fixed limits."""

    def __init__(
        self,
        credential_resolver: OpenAIPrivateCredentialResolverPort,
        output_configuration_binding_report: ProviderOutputConfigurationBindingReport | None,
        client_factory: OpenAIImageClientFactoryPort | None = None,
    ) -> None:
        self._credential_resolver = credential_resolver
        self._client_factory = client_factory or OpenAIImageSdkClientFactory()
        self._output_configuration = _capture_ready_output_configuration(
            output_configuration_binding_report
        )

    def invoke(self, request: ProviderPrivateTransportRequest) -> ProviderPrivateTransportResult:
        """Invoke exactly once, or fail closed without leaking private material."""

        output_configuration = self._output_configuration
        if not _is_valid_request_binding(request, output_configuration):
            return _runtime_failure()
        if request.reference_asset_handles:
            return _runtime_failure()
        if not isinstance(request.raw_prompt, str) or not request.raw_prompt.strip():
            return _runtime_failure()
        assert output_configuration is not None

        client: OpenAIImageClientPort | None = None
        try:
            credential = self._credential_resolver.resolve()
            if not isinstance(credential, str) or not credential:
                return _runtime_failure()
            client = self._client_factory.create(
                credential,
                timeout_seconds=_TIMEOUT_SECONDS,
                max_retries=_MAX_RETRIES,
            )
        except Exception:
            return _runtime_failure()
        try:
            response = client.generate_image(
                model=_model_id(request),
                prompt=request.raw_prompt,
                n=_IMAGE_COUNT,
                size=output_configuration.output_size,
                quality=output_configuration.output_quality,
            )
        except Exception as error:
            category = _classify_openai_failure(error)
            return (
                _provider_failure(category)
                if category == "provider_declared_failure"
                else _runtime_failure(category)
            )
        finally:
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass

        try:
            material, diagnostic_category = _decode_single_image(response)
        except Exception:
            return _runtime_failure("unknown_runtime_failure")
        if material is None:
            return _runtime_failure(diagnostic_category)
        return ProviderPrivateTransportResult("succeeded", material)


def _capture_ready_output_configuration(
    report: ProviderOutputConfigurationBindingReport | None,
) -> ProviderOutputConfigurationBindingDTO | None:
    """Capture only a defensively confirmed, ready immutable configuration."""

    if (
        report is None
        or report.status != "ready"
        or report.ready is not True
        or report.output_configuration is None
    ):
        return None
    confirmed = ProviderOutputConfigurationBindingService().validate(
        report.output_configuration,
        report.provider_configuration_normalization_report,
    )
    if (
        confirmed.status != "ready"
        or confirmed.ready is not True
        or confirmed.output_configuration != report.output_configuration
    ):
        return None
    return report.output_configuration


def _is_valid_request_binding(
    request: ProviderPrivateTransportRequest,
    output_configuration: ProviderOutputConfigurationBindingDTO | None,
) -> bool:
    selection = request.configuration_selection
    return bool(
        output_configuration is not None
        and request.attempt_id == selection.attempt_id
        and request.provider_reference == selection.provider_reference
        and request.profile_id == selection.profile_id
        and request.profile_version == selection.profile_version
        and request.attempt_id == output_configuration.attempt_id
        and request.provider_reference == output_configuration.provider_reference
        and request.profile_id == output_configuration.profile_id
        and request.profile_version == output_configuration.profile_version
        and selection.provider_id.availability == "known"
        and selection.provider_id.value == _OPENAI_PROVIDER_ID
        and selection.model_id.availability == "known"
        and selection.model_id.value == _OPENAI_MODEL_ID
        and output_configuration.model_id == _OPENAI_MODEL_ID
        and selection.model_id.value == output_configuration.model_id
    )


def _model_id(request: ProviderPrivateTransportRequest) -> str:
    value = request.configuration_selection.model_id.value
    assert isinstance(value, str)
    return value


def _decode_single_image(
    response: object,
) -> tuple[OpenAIInMemoryGeneratedImageMaterial | None, OpenAIFailureDiagnosticCategory | None]:
    data = getattr(response, "data", None)
    if not isinstance(data, (tuple, list)) or len(data) != 1:
        return None, "response_shape_failure"
    encoded = getattr(data[0], "b64_json", None)
    if not isinstance(encoded, str) or not encoded:
        return None, "response_shape_failure"
    if len(encoded) > _MAX_BASE64_CHARS:
        return None, "base64_validation_failure"
    try:
        decoded = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return None, "base64_validation_failure"
    if not decoded or len(decoded) > _MAX_DECODED_OUTPUT_BYTES:
        return None, "base64_validation_failure"
    return OpenAIInMemoryGeneratedImageMaterial(image_bytes=decoded), None


def _classify_openai_failure(error: Exception) -> OpenAIFailureDiagnosticCategory:
    """Classify only stable in-memory signals; never parse or retain error text."""

    try:
        if _is_provider_declared_failure(error):
            return "provider_declared_failure"
        if _has_exact_discriminator(error, {"insufficient_quota", "billing_hard_limit_reached"}):
            return "billing_or_quota_failure"
        if _has_status(error, {401, 403}):
            return "access_failure"
        if _has_status(error, {429}):
            return "rate_limit_failure"

        from openai import (
            APIConnectionError,
            APITimeoutError,
            AuthenticationError,
            BadRequestError,
            PermissionDeniedError,
            RateLimitError,
            UnprocessableEntityError,
        )
    except ImportError:
        return "unknown_runtime_failure"
    except Exception:
        return "unknown_runtime_failure"

    if isinstance(error, (AuthenticationError, PermissionDeniedError)):
        return "access_failure"
    if isinstance(error, RateLimitError):
        return "rate_limit_failure"
    if isinstance(error, APITimeoutError):
        return "timeout_failure"
    if isinstance(error, APIConnectionError):
        return "transport_failure"
    if isinstance(error, (BadRequestError, UnprocessableEntityError)):
        return "sdk_validation_failure"
    return "unknown_runtime_failure"


def _has_exact_discriminator(error: Exception, allowed: set[str]) -> bool:
    return getattr(error, "code", None) in allowed


def _has_status(error: Exception, allowed: set[int]) -> bool:
    return getattr(error, "status_code", None) in allowed


def _is_provider_declared_failure(error: Exception) -> bool:
    """Recognize only frozen, documented image-generation rejection markers."""

    return bool(
        getattr(error, "code", None) == "moderation_blocked"
        or getattr(error, "type", None) == "image_generation_user_error"
    )


def _provider_failure(
    diagnostic_category: OpenAIFailureDiagnosticCategory = "provider_declared_failure",
) -> ProviderPrivateTransportResult:
    return ProviderPrivateTransportResult("provider_failed", diagnostic_category=diagnostic_category)


def _runtime_failure(
    diagnostic_category: OpenAIFailureDiagnosticCategory | None = None,
) -> ProviderPrivateTransportResult:
    return ProviderPrivateTransportResult("runtime_failed", diagnostic_category=diagnostic_category)
