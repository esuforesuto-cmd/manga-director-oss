from __future__ import annotations

import base64
import inspect
from dataclasses import replace
from pathlib import Path

from manga_director.production.next_generation_authorized_execution_envelope import (
    AuthorizedGenerationExecutionEnvelopeDTO,
    AuthorizedGenerationExecutionEnvelopeValidationReport,
)
from manga_director.production.next_generation_generation_evidence import EvidenceValueDTO
from manga_director.production.next_generation_openai_private_composition import (
    compose_openai_private_invocation_adapter,
)
from manga_director.production.next_generation_provider_adapter_composition import (
    ProviderPrivateTransportRequest,
)
from manga_director.production.next_generation_provider_configuration import (
    ProviderConfigurationNormalizationReport,
    ProviderConfigurationSelectionDTO,
)
from manga_director.production.next_generation_provider_invocation import (
    ProviderGenerationInvocationPort,
    ProviderInvocationService,
)
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
    def __init__(self, values: dict[str, str] | None = None) -> None:
        self.values = values or {}
        self.calls: list[str] = []

    def __call__(self, name: str) -> str | None:
        self.calls.append(name)
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


def _reports():
    configuration = _configuration_report()
    output = ProviderOutputConfigurationBindingService().validate(
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
    assert output.ready is True
    return configuration, output


def _materialized() -> MaterializedGenerationInput:
    return MaterializedGenerationInput(
        attempt_id=ATTEMPT_ID,
        request_id="request:001",
        provider_reference=PROVIDER_REFERENCE,
        profile_id=PROFILE_ID,
        profile_version=PROFILE_VERSION,
        generation_intent_reference="intent:001",
        input_reference="input:001",
        raw_prompt=PROMPT,
    )


def _compose(
    selector: str | None = SELECTOR,
    lookup: _Lookup | None = None,
):
    configuration, output = _reports()
    fake_lookup = lookup or _Lookup({SELECTOR: SECRET})
    factory = _ClientFactory()
    adapter = compose_openai_private_invocation_adapter(
        selector,
        configuration,
        output,
        secret_lookup=fake_lookup,
        client_factory=factory,
    )
    return adapter, configuration, output, fake_lookup, factory


def test_explicit_selector_composes_exact_bound_adapter_without_lookup() -> None:
    adapter, _, _, lookup, factory = _compose()

    assert adapter is not None
    assert adapter.provider_reference == PROVIDER_REFERENCE
    assert lookup.calls == []
    assert factory.calls == []


def test_missing_blank_invalid_and_implicit_selectors_fail_before_lookup() -> None:
    for selector in (None, "", "private_openai_selector"):
        adapter, _, _, lookup, factory = _compose(selector)
        assert adapter is None
        assert lookup.calls == []
        assert factory.calls == []


def test_source_has_no_hardcoded_candidate_or_public_configuration_surface() -> None:
    source = (
        ROOT
        / "src/manga_director/production/next_generation_openai_private_composition.py"
    ).read_text(encoding="utf-8")

    for forbidden in (
        "MANGA_DIRECTOR_OPENAI_API_KEY",
        "os.environ",
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
    production_init = (ROOT / "src/manga_director/production/__init__.py").read_text(
        encoding="utf-8"
    )
    root_init = (ROOT / "src/manga_director/__init__.py").read_text(encoding="utf-8")
    assert "next_generation_openai_private_composition" not in production_init
    assert "next_generation_openai_private_composition" not in root_init


def test_non_ready_or_inconsistent_reports_fail_before_credential_activity() -> None:
    _, configuration, output, lookup, factory = _compose()
    blocked_configuration = configuration.model_copy(
        update={"status": "blocked", "ready": False, "selection": None}
    )
    blocked_output = output.model_copy(
        update={"status": "blocked", "ready": False, "output_configuration": None}
    )
    inconsistent_output = output.model_copy(
        update={
            "output_configuration": output.output_configuration.model_copy(
                update={"profile_id": "profile:other"}
            )
        }
    )

    for config, output_report in (
        (blocked_configuration, output),
        (configuration, blocked_output),
        (configuration, inconsistent_output),
    ):
        assert (
            compose_openai_private_invocation_adapter(
                SELECTOR,
                config,
                output_report,
                secret_lookup=lookup,
                client_factory=factory,
            )
            is None
        )

    assert lookup.calls == []
    assert factory.calls == []


def test_credential_lookup_is_deferred_until_valid_invocation() -> None:
    adapter, _, _, lookup, factory = _compose()
    assert adapter is not None

    result = adapter.invoke(_materialized())

    assert result.outcome == "succeeded"
    assert lookup.calls == [SELECTOR]
    assert factory.calls == [{"credential": SECRET, "timeout_seconds": 120, "max_retries": 0}]
    assert factory.client.calls == [
        {
            "model": "gpt-image-2-2026-04-21",
            "prompt": PROMPT,
            "n": 1,
            "size": "1536x1024",
            "quality": "low",
        }
    ]
    assert factory.client.closed == 1


def test_invalid_bindings_assets_and_empty_prompt_do_not_lookup_credential() -> None:
    adapter, _, _, lookup, factory = _compose()
    assert adapter is not None
    materialized = _materialized()
    invalid_inputs = (
        replace(materialized, attempt_id="attempt:other"),
        replace(materialized, provider_reference="provider:other"),
        replace(materialized, profile_id="profile:other"),
        replace(materialized, profile_version="v2"),
        replace(
            materialized,
            reference_asset_handles=(OpaqueReferenceAssetHandle("asset:001"),),
        ),
        replace(materialized, raw_prompt=""),
    )

    for invalid in invalid_inputs:
        assert adapter.invoke(invalid).outcome == "runtime_failed"

    assert lookup.calls == []
    assert factory.calls == []
    assert factory.client.calls == []


def test_serialized_invocation_report_redacts_selector_and_credential() -> None:
    adapter, _, _, lookup, factory = _compose()
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
    report = ProviderInvocationService().invoke(
        ATTEMPT_ID,
        SecureExecutionInputResolutionOutcome(resolution_report, _materialized()),
        adapter,
    ).report
    serialized = report.model_dump_json(fallback=lambda _: "", warnings=False)

    assert lookup.calls == [SELECTOR]
    assert factory.client.calls
    assert report.succeeded is True
    for private_value in (SELECTOR, SECRET, PROMPT, ENCODED_IMAGE):
        assert private_value not in serialized


def test_generic_port_signatures_are_unchanged() -> None:
    assert tuple(inspect.signature(ProviderGenerationInvocationPort.invoke).parameters) == (
        "self",
        "materialized_input",
    )
    assert tuple(ProviderPrivateTransportRequest.__dataclass_fields__) == (
        "attempt_id",
        "provider_reference",
        "profile_id",
        "profile_version",
        "configuration_selection",
        "raw_prompt",
        "reference_asset_handles",
    )
