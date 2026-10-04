from __future__ import annotations

import base64
from dataclasses import replace
from pathlib import Path

import pytest

from manga_director.production.next_generation_authorized_execution_envelope import (
    AuthorizedGenerationExecutionEnvelopeDTO,
    AuthorizedGenerationExecutionEnvelopeValidationReport,
)
from manga_director.production.next_generation_generation_evidence import EvidenceValueDTO
from manga_director.production.next_generation_openai_private_credentials import (
    ExactKeySecretManager,
    OpenAIPrivateCredentialResolver,
)
from manga_director.production.next_generation_openai_provider_adapter import (
    OpenAIImagePrivateTransport,
)
from manga_director.production.next_generation_provider_adapter_composition import (
    ProviderAdapterCompositionService,
    ProviderPrivateTransportRequest,
)
from manga_director.production.next_generation_provider_configuration import (
    ProviderConfigurationNormalizationReport,
    ProviderConfigurationSelectionDTO,
)
from manga_director.production.next_generation_provider_invocation import ProviderInvocationService
from manga_director.production.next_generation_provider_output_configuration import (
    ProviderOutputConfigurationBindingDTO,
    ProviderOutputConfigurationBindingService,
)
from manga_director.production.next_generation_secure_execution_input_resolution import (
    MaterializedGenerationInput,
    OpaqueReferenceAssetHandle,
    SecureExecutionInputResolutionOutcome,
    SecureExecutionInputResolutionReport,
)
from manga_director.security import CredentialManager

ROOT = Path(__file__).resolve().parents[1]
SELECTOR = "PRIVATE_OPENAI_SELECTOR"
SECRET = "PRIVATE-OPENAI-CREDENTIAL-VALUE"
PROMPT = "PRIVATE-OPENAI-PROMPT"
ENCODED_IMAGE = base64.b64encode(b"fake-image").decode("ascii")
ATTEMPT_ID = "attempt:001"
PROVIDER_REFERENCE = "provider:openai"
PROFILE_ID = "profile:manga"
PROFILE_VERSION = "v1"


class _Lookup:
    def __init__(self, values: dict[str, str] | None = None, error: Exception | None = None) -> None:
        self.values = values or {}
        self.error = error
        self.calls: list[str] = []

    def __call__(self, name: str) -> str | None:
        self.calls.append(name)
        if self.error is not None:
            raise self.error
        return self.values.get(name)


class _Image:
    def __init__(self, encoded: str) -> None:
        self.b64_json = encoded


class _Response:
    def __init__(self) -> None:
        self.data = (_Image(ENCODED_IMAGE),)


class _Client:
    def __init__(self) -> None:
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
    ) -> _Response:
        self.calls.append(
            {"model": model, "prompt": prompt, "n": n, "size": size, "quality": quality}
        )
        return _Response()

    def close(self) -> None:
        self.closed += 1


class _ClientFactory:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.client = _Client()

    def create(self, credential: str, *, timeout_seconds: int, max_retries: int) -> _Client:
        self.calls.append(
            {
                "credential": credential,
                "timeout_seconds": timeout_seconds,
                "max_retries": max_retries,
            }
        )
        return self.client


def _known(value: str) -> EvidenceValueDTO:
    return EvidenceValueDTO(availability="known", value=value)


def _configuration_report() -> ProviderConfigurationNormalizationReport:
    selection = ProviderConfigurationSelectionDTO(
        attempt_id=ATTEMPT_ID,
        provider_reference=PROVIDER_REFERENCE,
        profile_id=PROFILE_ID,
        profile_version=PROFILE_VERSION,
        provider_id=_known("openai"),
        model_id=_known("gpt-image-2-2026-04-21"),
        model_version=_known("v1"),
        workflow_id=EvidenceValueDTO(availability="unavailable"),
        workflow_version=EvidenceValueDTO(availability="unavailable"),
    )
    return ProviderConfigurationNormalizationReport.model_construct(
        authorized_execution_envelope_validation_report=object(),
        selection=selection,
        findings=(),
        status="ready",
        ready=True,
    )


def _output_configuration_report():
    configuration = _configuration_report()
    report = ProviderOutputConfigurationBindingService().validate(
        ProviderOutputConfigurationBindingDTO(
            attempt_id=ATTEMPT_ID,
            provider_reference=PROVIDER_REFERENCE,
            profile_id=PROFILE_ID,
            profile_version=PROFILE_VERSION,
            model_id="gpt-image-2-2026-04-21",
            output_size="1536x1024",
            output_quality="low",
        ),
        configuration,
    )
    assert report.ready is True
    return configuration, report


def _resolver(lookup: _Lookup | None = None) -> tuple[OpenAIPrivateCredentialResolver, _Lookup]:
    fake_lookup = lookup or _Lookup({SELECTOR: SECRET})
    manager = CredentialManager(ExactKeySecretManager(SELECTOR, fake_lookup))
    return OpenAIPrivateCredentialResolver(manager, SELECTOR), fake_lookup


def _transport_and_request(
    lookup: _Lookup | None = None,
) -> tuple[
    OpenAIImagePrivateTransport,
    ProviderPrivateTransportRequest,
    _Lookup,
    _ClientFactory,
]:
    configuration, output_configuration = _output_configuration_report()
    resolver, fake_lookup = _resolver(lookup)
    factory = _ClientFactory()
    transport = OpenAIImagePrivateTransport(resolver, output_configuration, factory)
    assert configuration.selection is not None
    request = ProviderPrivateTransportRequest(
        attempt_id=ATTEMPT_ID,
        provider_reference=PROVIDER_REFERENCE,
        profile_id=PROFILE_ID,
        profile_version=PROFILE_VERSION,
        configuration_selection=configuration.selection,
        raw_prompt=PROMPT,
    )
    return transport, request, fake_lookup, factory


def test_exact_selector_resolves_without_cache_or_exposure() -> None:
    resolver, lookup = _resolver()

    assert resolver.resolve() == SECRET
    assert resolver.resolve() == SECRET
    assert lookup.calls == [SELECTOR, SELECTOR]
    assert not hasattr(resolver, "selector")
    assert not hasattr(resolver, "credential")
    assert not hasattr(resolver, "__dict__")
    assert SELECTOR not in repr(resolver) + str(resolver)
    assert SECRET not in repr(resolver) + str(resolver)


def test_exact_key_manager_rejects_wrong_selector_without_lookup_or_fallback() -> None:
    lookup = _Lookup({SELECTOR: SECRET, "OTHER_SELECTOR": "other"})
    manager = ExactKeySecretManager(SELECTOR, lookup)

    with pytest.raises(Exception) as error:
        manager.get("OTHER_SELECTOR")

    assert str(error.value) == ""
    assert lookup.calls == []
    assert not hasattr(manager, "__dict__")
    assert SELECTOR not in repr(manager) + str(manager)
    assert SECRET not in repr(manager) + str(manager)


@pytest.mark.parametrize(
    "lookup",
    (
        _Lookup({}),
        _Lookup({SELECTOR: "   "}),
        _Lookup(error=RuntimeError("PRIVATE-LOOKUP-DETAIL")),
    ),
)
def test_missing_blank_and_native_failure_are_redacted(lookup: _Lookup) -> None:
    resolver, actual_lookup = _resolver(lookup)

    with pytest.raises(Exception) as error:
        resolver.resolve()

    assert actual_lookup.calls == [SELECTOR]
    assert str(error.value) == ""
    assert "PRIVATE-LOOKUP-DETAIL" not in repr(error.value)
    assert SELECTOR not in repr(error.value)
    assert SECRET not in repr(error.value)


def test_source_uses_only_direct_lookup_and_no_public_or_serializable_surface() -> None:
    source = (
        ROOT
        / "src/manga_director/production/next_generation_openai_private_credentials.py"
    ).read_text(encoding="utf-8")

    for forbidden in (
        "os.environ",
        ".items()",
        "glob",
        "dotenv",
        "CredentialReference",
        "BaseModel",
        "DirectorModel",
        "logging",
        "model_dump",
        "open(",
        "requests.",
        "httpx.",
    ):
        assert forbidden not in source
    assert "os.getenv" in source
    production_init = (ROOT / "src/manga_director/production/__init__.py").read_text(
        encoding="utf-8"
    )
    root_init = (ROOT / "src/manga_director/__init__.py").read_text(encoding="utf-8")
    assert "next_generation_openai_private_credentials" not in production_init
    assert "next_generation_openai_private_credentials" not in root_init


@pytest.mark.parametrize(
    "update",
    (
        {"attempt_id": "attempt:other"},
        {"provider_reference": "provider:other"},
        {"profile_id": "profile:other"},
        {"profile_version": "v2"},
    ),
)
def test_invalid_transport_bindings_do_not_resolve_credentials(update: dict[str, str]) -> None:
    transport, request, lookup, factory = _transport_and_request()

    result = transport.invoke(replace(request, **update))

    assert result.outcome == "runtime_failed"
    assert lookup.calls == []
    assert factory.calls == []


def test_invalid_model_output_configuration_assets_and_prompt_do_not_resolve_credentials() -> None:
    transport, request, lookup, factory = _transport_and_request()
    altered_selection = request.configuration_selection.model_copy(
        update={"model_id": _known("gpt-image-other")}
    )
    invalid_requests = (
        replace(request, configuration_selection=altered_selection),
        replace(request, reference_asset_handles=(OpaqueReferenceAssetHandle("asset:001"),)),
        replace(request, raw_prompt=""),
    )

    for invalid in invalid_requests:
        assert transport.invoke(invalid).outcome == "runtime_failed"

    assert lookup.calls == []
    assert factory.calls == []


def test_non_ready_output_configuration_and_resolver_failure_do_not_create_client() -> None:
    _, request, _, _ = _transport_and_request()
    resolver, missing_lookup = _resolver(_Lookup({}))
    factory = _ClientFactory()
    transport = OpenAIImagePrivateTransport(resolver, None, factory)

    assert transport.invoke(request).outcome == "runtime_failed"
    assert missing_lookup.calls == []
    assert factory.calls == []

    transport, request, failing_lookup, failing_factory = _transport_and_request(_Lookup({}))
    assert transport.invoke(request).outcome == "runtime_failed"
    assert failing_lookup.calls == [SELECTOR]
    assert failing_factory.calls == []
    assert failing_factory.client.calls == []


def test_provider_invocation_report_redacts_selector_and_credential() -> None:
    configuration, output_configuration = _output_configuration_report()
    resolver, lookup = _resolver()
    factory = _ClientFactory()
    transport = OpenAIImagePrivateTransport(resolver, output_configuration, factory)
    adapter = ProviderAdapterCompositionService().compose(configuration, transport)
    assert adapter is not None

    envelope = AuthorizedGenerationExecutionEnvelopeDTO(
        attempt_id=ATTEMPT_ID,
        request_id="request:001",
        provider_reference=PROVIDER_REFERENCE,
        authorization_ids=("authorization:001",),
        profile_id=PROFILE_ID,
        profile_version=PROFILE_VERSION,
        generation_intent_reference="intent:001",
        input_reference="input:001",
    )
    authorized = AuthorizedGenerationExecutionEnvelopeValidationReport.model_construct(
        execution_authorization_validation_report=object(),
        envelopes=(envelope,),
        findings=(),
        status="ready",
        ready=True,
    )
    resolution_report = SecureExecutionInputResolutionReport.model_construct(
        authorized_execution_envelope_validation_report=authorized,
        attempt_id=ATTEMPT_ID,
        findings=(),
        status="ready",
        ready=True,
        input_materialized=True,
        reference_assets_resolved=True,
    )
    materialized = MaterializedGenerationInput(
        attempt_id=ATTEMPT_ID,
        request_id="request:001",
        provider_reference=PROVIDER_REFERENCE,
        profile_id=PROFILE_ID,
        profile_version=PROFILE_VERSION,
        generation_intent_reference="intent:001",
        input_reference="input:001",
        raw_prompt=PROMPT,
    )
    report = ProviderInvocationService().invoke(
        ATTEMPT_ID,
        SecureExecutionInputResolutionOutcome(resolution_report, materialized),
        adapter,
    ).report
    serialized = report.model_dump_json(fallback=lambda _: "", warnings=False)

    assert lookup.calls == [SELECTOR]
    assert factory.client.calls
    assert report.succeeded is True
    for private_value in (SELECTOR, SECRET, PROMPT, ENCODED_IMAGE):
        assert private_value not in serialized
