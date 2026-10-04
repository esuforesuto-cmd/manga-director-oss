"""Focused fake-only contracts for the internal OpenAI provider adapter."""

from __future__ import annotations

import base64
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    RateLimitError,
)

from manga_director.production.next_generation_authorized_execution_envelope import (
    AuthorizedGenerationExecutionEnvelopeDTO,
    AuthorizedGenerationExecutionEnvelopeValidationService,
)
from manga_director.production.next_generation_execution_authorization import (
    ExecutionAuthorizationRecordDTO,
    ExecutionAuthorizationValidationService,
)
from manga_director.production.next_generation_generation_evidence import (
    EvidenceValueDTO,
    GenerationIdentityBindingDTO,
    GenerationInputEvidenceDTO,
)
from manga_director.production.next_generation_openai_provider_adapter import (
    OpenAIImagePrivateTransport,
    OpenAIInMemoryGeneratedImageMaterial,
)
from manga_director.production.next_generation_pre_execution_readiness import (
    PreExecutionReadinessInputDTO,
    PreExecutionReadinessService,
)
from manga_director.production.next_generation_provider_adapter_composition import (
    ProviderAdapterCompositionService,
)
from manga_director.production.next_generation_provider_capability_negotiation import (
    GenerationCapabilityRequirementDTO,
    ProviderCapabilityDeclarationDTO,
    ProviderCapabilityNegotiationService,
    ProviderCapabilityStateDTO,
)
from manga_director.production.next_generation_provider_configuration import (
    AuthoritativeProviderConfigurationSnapshot,
    ProviderConfigurationNormalizationService,
)
from manga_director.production.next_generation_provider_invocation import ProviderInvocationService
from manga_director.production.next_generation_provider_output_configuration import (
    ProviderOutputConfigurationBindingDTO,
    ProviderOutputConfigurationBindingService,
)
from manga_director.production.next_generation_secure_execution_input_resolution import (
    AuthoritativeExecutionInputSnapshot,
    OpaqueReferenceAssetHandle,
    SecureExecutionInputResolutionOutcome,
    SecureExecutionInputResolutionService,
)
from manga_director.production.next_generation_structured_generation_request import (
    GenerationProductionProfileDTO,
    StructuredGenerationRequestDTO,
    StructuredGenerationRequestValidationService,
)

ROOT = Path(__file__).resolve().parents[1]
PROMPT = "PRIVATE-PROMPT-DO-NOT-LEAK"
SECRET = "PRIVATE-API-KEY-DO-NOT-LEAK"
ENCODED_IMAGE = base64.b64encode(b"fake-image-bytes").decode("ascii")
PRIVATE_CREDENTIAL_ID = "credential:openai-production"
PRIVATE_ENDPOINT = "https://provider.invalid/v1/images"
PRIVATE_PATH = r"C:\private\generated-image.png"
PRIVATE_REQUEST_ID = "provider-request-id:private-001"
PRIVATE_HEADERS = "authorization:bearer-private-value"


@dataclass
class _Image:
    b64_json: str | None


@dataclass
class _Response:
    data: object


class _ProviderError(Exception):
    def __init__(
        self,
        *,
        code: str | None = None,
        type_: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(
            " | ".join(
                (
                    "PRIVATE-NATIVE-EXCEPTION-DO-NOT-LEAK",
                    PRIVATE_CREDENTIAL_ID,
                    PRIVATE_ENDPOINT,
                    PRIVATE_PATH,
                    PRIVATE_REQUEST_ID,
                    PRIVATE_HEADERS,
                    "traceback",
                )
            )
        )
        self.code = code
        self.type = type_
        self.status_code = status_code


class _CredentialResolver:
    def __init__(self, value: object = SECRET) -> None:
        self.value = value
        self.calls = 0

    def resolve(self) -> str:
        self.calls += 1
        if isinstance(self.value, Exception):
            raise self.value
        return self.value  # type: ignore[return-value]


class _Client:
    def __init__(self, result: object = _Response([_Image(ENCODED_IMAGE)])) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []
        self.closed = 0

    def generate_image(
        self,
        *,
        model: str,
        prompt: str,
        n: int,
        size: str,
        quality: str,
    ) -> object:
        self.calls.append(
            {"model": model, "prompt": prompt, "n": n, "size": size, "quality": quality}
        )
        if isinstance(self.result, Exception):
            raise self.result
        return self.result

    def close(self) -> None:
        self.closed += 1


class _ClientFactory:
    def __init__(self, client: _Client | None = None) -> None:
        self.client = client or _Client()
        self.calls: list[dict[str, object]] = []

    def create(self, credential: str, *, timeout_seconds: int, max_retries: int) -> _Client:
        self.calls.append(
            {
                "credential": credential,
                "timeout_seconds": timeout_seconds,
                "max_retries": max_retries,
            }
        )
        return self.client


class _InputResolver:
    def resolve(self, input_reference: str) -> AuthoritativeExecutionInputSnapshot | None:
        if input_reference != "input:001":
            return None
        return AuthoritativeExecutionInputSnapshot.from_prompt_material(
            input_reference="input:001",
            generation_intent_reference="intent:001",
            raw_prompt_material=PROMPT,
            required_reference_asset_ids=(),
        )


class _AssetResolver:
    def resolve(self, reference_asset_id: str) -> OpaqueReferenceAssetHandle | None:
        return None


def _value(value: object | None = None, availability: str = "known") -> EvidenceValueDTO:
    return EvidenceValueDTO(
        availability=availability,  # type: ignore[arg-type]
        value=value if availability == "known" else None,
    )


def _chain():
    requirements = (
        GenerationCapabilityRequirementDTO(capability_id="text_prompt", requirement_level="required"),
    )
    profile = GenerationProductionProfileDTO(
        profile_id="profile:manga", profile_version="v1", capability_requirements=requirements
    )
    request = StructuredGenerationRequestDTO(
        request_id="request:001",
        target_page_reference="page:001",
        generation_intent_reference="intent:001",
        input=GenerationInputEvidenceDTO(input_reference="input:001"),
        capability_requirements=requirements,
        provenance_reference="provenance:001",
        profile_id="profile:manga",
        profile_version="v1",
        identity_bindings=(
            GenerationIdentityBindingDTO(
                character_id="character:001",
                identity_id="identity:001",
                identity_version="v1",
                reference_asset_ids=(),
            ),
        ),
    )
    request_report = StructuredGenerationRequestValidationService().validate(request, profile)
    negotiation = ProviderCapabilityNegotiationService().validate(
        requirements,
        ProviderCapabilityDeclarationDTO(
            provider_reference="provider:openai",
            capability_states=(
                ProviderCapabilityStateDTO(capability_id="text_prompt", state="supported"),
            ),
        ),
    )
    readiness = PreExecutionReadinessService().validate(
        PreExecutionReadinessInputDTO(
            request_validation_report=request_report,
            capability_negotiation_report=negotiation,
            provider_reference="provider:openai",
        )
    )
    authorization = ExecutionAuthorizationValidationService().validate(
        readiness,
        (
            ExecutionAuthorizationRecordDTO(
                authorization_id="authorization:001",
                authorizer_id="human:editor-a",
                authorized_at=datetime(2026, 8, 22, 12, 0, tzinfo=UTC),
                request_id="request:001",
                provider_reference="provider:openai",
            ),
        ),
    )
    authorized = AuthorizedGenerationExecutionEnvelopeValidationService().validate(
        (
            AuthorizedGenerationExecutionEnvelopeDTO(
                attempt_id="attempt:001",
                request_id="request:001",
                provider_reference="provider:openai",
                authorization_ids=("authorization:001",),
                profile_id="profile:manga",
                profile_version="v1",
                generation_intent_reference="intent:001",
                input_reference="input:001",
            ),
        ),
        authorization,
    )
    configuration = ProviderConfigurationNormalizationService().normalize(
        "attempt:001",
        AuthoritativeProviderConfigurationSnapshot(
            attempt_id="attempt:001",
            provider_reference="provider:openai",
            profile_id="profile:manga",
            profile_version="v1",
            provider_id=_value("openai"),
            model_id=_value("gpt-image-2-2026-04-21"),
            model_version=_value("v1"),
            workflow_id=_value(availability="unavailable"),
            workflow_version=_value(availability="unavailable"),
            requested_seed=_value(99),
        ),
        authorized,
    )
    resolution = SecureExecutionInputResolutionService().resolve(
        "attempt:001", authorized, _InputResolver(), _AssetResolver()
    )
    output_configuration = ProviderOutputConfigurationBindingService().validate(
        ProviderOutputConfigurationBindingDTO(
            attempt_id="attempt:001",
            provider_reference="provider:openai",
            profile_id="profile:manga",
            profile_version="v1",
            model_id="gpt-image-2-2026-04-21",
            output_size="1536x1024",
            output_quality="low",
        ),
        configuration,
    )
    assert configuration.selection is not None
    assert output_configuration.ready is True
    assert resolution.materialized_input is not None
    return configuration, output_configuration, resolution


def _adapter(
    resolver: _CredentialResolver | None = None, factory: _ClientFactory | None = None
):
    configuration, output_configuration, resolution = _chain()
    credential_resolver = resolver or _CredentialResolver()
    client_factory = factory or _ClientFactory()
    transport = OpenAIImagePrivateTransport(
        credential_resolver,
        output_configuration,
        client_factory,
    )
    adapter = ProviderAdapterCompositionService().compose(configuration, transport)
    assert adapter is not None
    return adapter, resolution, credential_resolver, client_factory


def test_prompt_only_request_is_exact_bound_and_sdk_controls_are_fixed() -> None:
    adapter, resolution, resolver, factory = _adapter()
    assert resolution.materialized_input is not None

    result = adapter.invoke(resolution.materialized_input)

    assert result.outcome == "succeeded"
    assert result.output_handle is not None
    assert resolver.calls == 1
    assert factory.calls == [
        {"credential": SECRET, "timeout_seconds": 120, "max_retries": 0},
    ]
    assert factory.client.calls == [
        {
            "model": "gpt-image-2-2026-04-21",
            "prompt": PROMPT,
            "n": 1,
            "size": "1536x1024",
            "quality": "low",
        },
    ]
    assert factory.client.closed == 1
    assert isinstance(result.output_handle.opaque_value, OpenAIInMemoryGeneratedImageMaterial)
    assert result.output_handle.opaque_value.image_bytes == b"fake-image-bytes"
    assert not hasattr(resolution.materialized_input, "effective_seed")


@pytest.mark.parametrize(
    "updates",
    (
        {"attempt_id": "attempt:other"},
        {"provider_reference": "provider:other"},
        {"profile_id": "profile:other"},
        {"profile_version": "v2"},
    ),
)
def test_binding_mismatch_fails_closed_before_credential_or_client(
    updates: dict[str, str],
) -> None:
    adapter, resolution, resolver, factory = _adapter()
    assert resolution.materialized_input is not None
    result = adapter.invoke(replace(resolution.materialized_input, **updates))
    assert result.outcome == "runtime_failed"
    assert resolver.calls == 0
    assert factory.calls == []


@pytest.mark.parametrize("provider_id", (_value("other"), _value(availability="unavailable")))
def test_unknown_openai_provider_binding_fails_closed_before_credential(
    provider_id: EvidenceValueDTO,
) -> None:
    configuration, output_configuration, resolution = _chain()
    assert configuration.selection is not None
    altered = configuration.selection.model_copy(update={"provider_id": provider_id})
    resolver = _CredentialResolver()
    factory = _ClientFactory()
    adapter = ProviderAdapterCompositionService().compose(
        configuration.model_copy(update={"selection": altered}),
        OpenAIImagePrivateTransport(resolver, output_configuration, factory),
    )
    assert adapter is not None and resolution.materialized_input is not None
    assert adapter.invoke(resolution.materialized_input).outcome == "runtime_failed"
    assert resolver.calls == 0
    assert factory.calls == []


@pytest.mark.parametrize("state", ("missing", "non_ready", "malformed"))
def test_unavailable_output_configuration_fails_before_credential_or_client(state: str) -> None:
    configuration, output_configuration, resolution = _chain()
    if state == "missing":
        report = None
    elif state == "non_ready":
        report = output_configuration.model_copy(
            update={"status": "blocked", "ready": False, "output_configuration": None}
        )
    else:
        assert output_configuration.output_configuration is not None
        report = output_configuration.model_copy(
            update={
                "output_configuration": output_configuration.output_configuration.model_copy(
                    update={"output_size": "auto"}
                )
            }
        )
    resolver = _CredentialResolver()
    factory = _ClientFactory()
    adapter = ProviderAdapterCompositionService().compose(
        configuration,
        OpenAIImagePrivateTransport(resolver, report, factory),
    )

    assert adapter is not None and resolution.materialized_input is not None
    assert adapter.invoke(resolution.materialized_input).outcome == "runtime_failed"
    assert resolver.calls == 0
    assert factory.calls == []


def test_model_mismatch_fails_closed_before_credential_or_client() -> None:
    configuration, output_configuration, resolution = _chain()
    assert configuration.selection is not None
    altered = configuration.selection.model_copy(update={"model_id": _value("gpt-image-other")})
    resolver = _CredentialResolver()
    factory = _ClientFactory()
    adapter = ProviderAdapterCompositionService().compose(
        configuration.model_copy(update={"selection": altered}),
        OpenAIImagePrivateTransport(resolver, output_configuration, factory),
    )

    assert adapter is not None and resolution.materialized_input is not None
    assert adapter.invoke(resolution.materialized_input).outcome == "runtime_failed"
    assert resolver.calls == 0
    assert factory.calls == []


def test_reference_assets_fail_closed_before_credential_client_or_network_boundary() -> None:
    adapter, resolution, resolver, factory = _adapter()
    assert resolution.materialized_input is not None
    reference_bound = replace(
        resolution.materialized_input,
        reference_asset_handles=(OpaqueReferenceAssetHandle("asset:001", object()),),
    )

    assert adapter.invoke(reference_bound).outcome == "runtime_failed"
    assert resolver.calls == 0
    assert factory.calls == []


def test_empty_prompt_fails_closed_before_credential_or_client() -> None:
    adapter, resolution, resolver, factory = _adapter()
    assert resolution.materialized_input is not None

    result = adapter.invoke(replace(resolution.materialized_input, raw_prompt=""))

    assert result.outcome == "runtime_failed"
    assert resolver.calls == 0
    assert factory.calls == []


@pytest.mark.parametrize(
    "response",
    (
        _Response([]),
        _Response([_Image(ENCODED_IMAGE), _Image(ENCODED_IMAGE)]),
        _Response([_Image(None)]),
        _Response([_Image("not-base64")]),
        _Response([_Image(base64.b64encode(b"x" * (25 * 1024 * 1024 + 1)).decode("ascii"))]),
    ),
)
def test_only_one_strict_b64_json_output_within_memory_limit_is_accepted(response: object) -> None:
    adapter, resolution, _, factory = _adapter(factory=_ClientFactory(_Client(response)))
    assert resolution.materialized_input is not None

    result = adapter.invoke(resolution.materialized_input)

    assert result.outcome == "runtime_failed"
    assert result.output_handle is None
    assert len(factory.client.calls) == 1


@pytest.mark.parametrize(
    "error, expected",
    (
        (_ProviderError(code="moderation_blocked"), "provider_failed"),
        (_ProviderError(type_="image_generation_user_error"), "provider_failed"),
        (_ProviderError(), "runtime_failed"),
        (TimeoutError("PRIVATE-TIMEOUT-DO-NOT-LEAK"), "runtime_failed"),
    ),
)
def test_private_errors_have_closed_classification(error: Exception, expected: str) -> None:
    adapter, resolution, _, factory = _adapter(factory=_ClientFactory(_Client(error)))
    assert resolution.materialized_input is not None
    result = adapter.invoke(resolution.materialized_input)
    assert result.outcome == expected
    assert result.output_handle is None
    assert len(factory.client.calls) == 1


def _bare_sdk_error(error_type: type[Exception]) -> Exception:
    """Build a fake-safe SDK exception without a request or response object."""

    error = BaseException.__new__(error_type)
    Exception.__init__(error, "PRIVATE-NATIVE-EXCEPTION-DO-NOT-LEAK")
    return error


@pytest.mark.parametrize(
    ("error", "outcome", "failure_category", "diagnostic_category"),
    (
        (
            _bare_sdk_error(AuthenticationError),
            "runtime_failed",
            "runtime_failure",
            "access_failure",
        ),
        (
            _ProviderError(code="insufficient_quota"),
            "runtime_failed",
            "runtime_failure",
            "billing_or_quota_failure",
        ),
        (
            _bare_sdk_error(RateLimitError),
            "runtime_failed",
            "runtime_failure",
            "rate_limit_failure",
        ),
        (
            _bare_sdk_error(APIConnectionError),
            "runtime_failed",
            "runtime_failure",
            "transport_failure",
        ),
        (
            _bare_sdk_error(APITimeoutError),
            "runtime_failed",
            "runtime_failure",
            "timeout_failure",
        ),
        (
            _bare_sdk_error(BadRequestError),
            "runtime_failed",
            "runtime_failure",
            "sdk_validation_failure",
        ),
        (
            _ProviderError(code="moderation_blocked"),
            "provider_failed",
            "provider_declared_failure",
            "provider_declared_failure",
        ),
        (
            _ProviderError(status_code=500),
            "runtime_failed",
            "runtime_failure",
            "unknown_runtime_failure",
        ),
    ),
)
def test_approved_sdk_and_machine_readable_failures_have_bounded_diagnostics(
    error: Exception,
    outcome: str,
    failure_category: str,
    diagnostic_category: str,
) -> None:
    adapter, resolution, _, factory = _adapter(factory=_ClientFactory(_Client(error)))
    assert resolution.materialized_input is not None

    runtime = adapter.invoke(resolution.materialized_input)
    report_adapter, report_resolution, _, report_factory = _adapter(
        factory=_ClientFactory(_Client(error))
    )
    report = ProviderInvocationService().invoke(
        "attempt:001",
        SecureExecutionInputResolutionOutcome(
            report=report_resolution.report,
            materialized_input=report_resolution.materialized_input,
        ),
        report_adapter,
    ).report

    assert runtime.outcome == outcome
    assert runtime.failure_category == failure_category
    assert runtime.diagnostic_category == diagnostic_category
    assert [finding.diagnostic_category for finding in report.findings] == [diagnostic_category]
    serialized = report.model_dump_json()
    for prohibited in (
        "PRIVATE-NATIVE-EXCEPTION-DO-NOT-LEAK",
        "private-code",
        "insufficient_quota",
        "moderation_blocked",
        PRIVATE_CREDENTIAL_ID,
        PRIVATE_ENDPOINT,
        PRIVATE_PATH,
        PRIVATE_REQUEST_ID,
        PRIVATE_HEADERS,
        "traceback",
    ):
        assert prohibited not in serialized
    assert len(factory.client.calls) == 1
    assert len(report_factory.client.calls) == 1


@pytest.mark.parametrize(
    ("response", "diagnostic_category"),
    (
        (_Response([]), "response_shape_failure"),
        (_Response([_Image(ENCODED_IMAGE), _Image(ENCODED_IMAGE)]), "response_shape_failure"),
        (_Response([_Image(None)]), "response_shape_failure"),
        (_Response([_Image("not-base64")]), "base64_validation_failure"),
        (
            _Response([_Image(base64.b64encode(b"x" * (25 * 1024 * 1024 + 1)).decode("ascii"))]),
            "base64_validation_failure",
        ),
    ),
)
def test_output_validation_has_bounded_response_and_base64_diagnostics(
    response: object, diagnostic_category: str
) -> None:
    adapter, resolution, _, factory = _adapter(factory=_ClientFactory(_Client(response)))
    assert resolution.materialized_input is not None

    result = adapter.invoke(resolution.materialized_input)

    assert result.outcome == "runtime_failed"
    assert result.failure_category == "runtime_failure"
    assert result.diagnostic_category == diagnostic_category
    assert len(factory.client.calls) == 1


def test_message_content_is_never_used_for_failure_classification() -> None:
    error = RuntimeError("insufficient_quota moderation_blocked 429 PRIVATE-DO-NOT-LEAK")
    adapter, resolution, _, factory = _adapter(factory=_ClientFactory(_Client(error)))
    assert resolution.materialized_input is not None

    result = adapter.invoke(resolution.materialized_input)

    assert result.diagnostic_category == "unknown_runtime_failure"
    assert len(factory.client.calls) == 1


def test_provider_invocation_report_is_redacted_and_repeatable() -> None:
    adapter, resolution, _, factory = _adapter()
    outcome = SecureExecutionInputResolutionOutcome(
        report=resolution.report,
        materialized_input=resolution.materialized_input,
    )
    first = ProviderInvocationService().invoke("attempt:001", outcome, adapter)
    second = ProviderInvocationService().invoke("attempt:001", outcome, adapter)
    error_adapter, error_resolution, _, error_factory = _adapter(
        factory=_ClientFactory(_Client(_ProviderError()))
    )
    error_outcome = SecureExecutionInputResolutionOutcome(
        report=error_resolution.report,
        materialized_input=error_resolution.materialized_input,
    )
    error_report = ProviderInvocationService().invoke("attempt:001", error_outcome, error_adapter).report
    serialized = first.report.model_dump_json() + error_report.model_dump_json()

    assert first.report.model_dump(mode="json") == second.report.model_dump(mode="json")
    for private_value in (
        PROMPT,
        SECRET,
        ENCODED_IMAGE,
        "PRIVATE-NATIVE-EXCEPTION-DO-NOT-LEAK",
        PRIVATE_CREDENTIAL_ID,
        PRIVATE_ENDPOINT,
        PRIVATE_PATH,
        PRIVATE_REQUEST_ID,
        PRIVATE_HEADERS,
        "traceback",
    ):
        assert private_value not in serialized
    assert len(factory.client.calls) == 2
    assert len(error_factory.client.calls) == 1


def test_no_mutation_and_internal_surface_only() -> None:
    adapter, resolution, _, factory = _adapter()
    assert resolution.materialized_input is not None
    before = (resolution.report.model_dump(mode="json"), resolution.materialized_input.raw_prompt)
    adapter.invoke(resolution.materialized_input)
    assert (resolution.report.model_dump(mode="json"), resolution.materialized_input.raw_prompt) == before
    assert factory.client.closed == 1

    source = (
        ROOT / "src/manga_director/production/next_generation_openai_provider_adapter.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "manga_director.adapters",
        "manga_director.agents",
        "manga_director.workflow",
        "GenerationEvidenceEnvelopeDTO",
        "CredentialManager",
        "open(",
        "requests.",
        "httpx.",
        "logging",
        "datetime",
    ):
        assert forbidden not in source
    production_init = (ROOT / "src/manga_director/production/__init__.py").read_text(
        encoding="utf-8"
    )
    root_init = (ROOT / "src/manga_director/__init__.py").read_text(encoding="utf-8")
    assert "next_generation_openai_provider_adapter" not in production_init
    assert "next_generation_openai_provider_adapter" not in root_init
