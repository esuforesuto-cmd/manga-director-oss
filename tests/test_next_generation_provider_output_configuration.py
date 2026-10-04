"""Focused contracts for internal provider output configuration binding."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

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
    GenerationInputEvidenceDTO,
)
from manga_director.production.next_generation_pre_execution_readiness import (
    PreExecutionReadinessInputDTO,
    PreExecutionReadinessService,
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
from manga_director.production.next_generation_provider_output_configuration import (
    ProviderOutputConfigurationBindingDTO,
    ProviderOutputConfigurationBindingService,
    ProviderOutputConfigurationFindingDTO,
)
from manga_director.production.next_generation_structured_generation_request import (
    GenerationProductionProfileDTO,
    StructuredGenerationRequestDTO,
    StructuredGenerationRequestValidationService,
)

ROOT = Path(__file__).resolve().parents[1]


def _value(value: object | None = None, availability: str = "known") -> EvidenceValueDTO:
    return EvidenceValueDTO(
        availability=availability,  # type: ignore[arg-type]
        value=value if availability == "known" else None,
    )


def _configuration_report(**updates: object):
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
    values: dict[str, object] = {
        "attempt_id": "attempt:001",
        "provider_reference": "provider:openai",
        "profile_id": "profile:manga",
        "profile_version": "v1",
        "provider_id": _value("openai"),
        "model_id": _value("gpt-image-2-2026-04-21"),
        "model_version": _value("2026-04-21"),
        "workflow_id": _value(availability="unavailable"),
        "workflow_version": _value(availability="unavailable"),
    }
    values.update(updates)
    return ProviderConfigurationNormalizationService().normalize(
        "attempt:001",
        AuthoritativeProviderConfigurationSnapshot(**values),  # type: ignore[arg-type]
        authorized,
    )


def _binding(**updates: str) -> ProviderOutputConfigurationBindingDTO:
    values = {
        "attempt_id": "attempt:001",
        "provider_reference": "provider:openai",
        "profile_id": "profile:manga",
        "profile_version": "v1",
        "model_id": "gpt-image-2-2026-04-21",
        "output_size": "1536x1024",
        "output_quality": "low",
    }
    values.update(updates)
    return ProviderOutputConfigurationBindingDTO(**values)


def test_approved_smoke_configuration_passes_general_rules() -> None:
    report = ProviderOutputConfigurationBindingService().validate(_binding(), _configuration_report())

    assert report.status == "ready"
    assert report.ready is True
    assert report.output_configuration == _binding()
    assert report.findings == ()


@pytest.mark.parametrize("size", ("1024x640", "1024x1024", "3072x1024", "3840x2160"))
def test_general_size_rules_accept_valid_explicit_sizes(size: str) -> None:
    report = ProviderOutputConfigurationBindingService().validate(
        _binding(output_size=size), _configuration_report()
    )

    assert report.ready is True


@pytest.mark.parametrize(
    ("size", "code"),
    (
        ("auto", "OUTPUT_SIZE_AUTO_FORBIDDEN"),
        ("1536 x1024", "OUTPUT_SIZE_MALFORMED"),
        ("1536x 1024", "OUTPUT_SIZE_MALFORMED"),
        ("01536x1024", "OUTPUT_SIZE_MALFORMED"),
        ("1536x01024", "OUTPUT_SIZE_MALFORMED"),
        ("1000x1024", "OUTPUT_SIZE_UNSUPPORTED"),
        ("3856x1024", "OUTPUT_SIZE_UNSUPPORTED"),
        ("3088x1024", "OUTPUT_SIZE_UNSUPPORTED"),
        ("16x16", "OUTPUT_SIZE_UNSUPPORTED"),
        ("3840x3840", "OUTPUT_SIZE_UNSUPPORTED"),
    ),
)
def test_invalid_or_unsupported_size_fails_closed(size: str, code: str) -> None:
    report = ProviderOutputConfigurationBindingService().validate(
        _binding(output_size=size), _configuration_report()
    )

    assert report.status == "blocked"
    assert report.ready is False
    assert report.output_configuration is None
    assert code in {finding.code for finding in report.findings}


@pytest.mark.parametrize("quality", ("low", "medium", "high"))
def test_closed_quality_vocabulary_accepts_supported_values(quality: str) -> None:
    report = ProviderOutputConfigurationBindingService().validate(
        _binding(output_quality=quality), _configuration_report()
    )

    assert report.ready is True


@pytest.mark.parametrize(
    ("quality", "code"),
    (("auto", "OUTPUT_QUALITY_AUTO_FORBIDDEN"), ("ultra", "OUTPUT_QUALITY_UNSUPPORTED")),
)
def test_auto_or_unknown_quality_fails_closed(quality: str, code: str) -> None:
    report = ProviderOutputConfigurationBindingService().validate(
        _binding(output_quality=quality), _configuration_report()
    )

    assert report.status == "blocked"
    assert code in {finding.code for finding in report.findings}


@pytest.mark.parametrize(
    ("updates", "code"),
    (
        ({"attempt_id": "attempt:other"}, "ATTEMPT_BINDING_MISMATCH"),
        ({"provider_reference": "provider:other"}, "PROVIDER_BINDING_MISMATCH"),
        ({"profile_id": "profile:other"}, "PROFILE_ID_BINDING_MISMATCH"),
        ({"profile_version": "v2"}, "PROFILE_VERSION_BINDING_MISMATCH"),
        ({"model_id": "gpt-image-2-2026-04-22"}, "MODEL_BINDING_MISMATCH"),
    ),
)
def test_exact_bindings_fail_closed(updates: dict[str, str], code: str) -> None:
    report = ProviderOutputConfigurationBindingService().validate(
        _binding(**updates), _configuration_report()
    )

    assert report.status == "blocked"
    assert code in {finding.code for finding in report.findings}


@pytest.mark.parametrize(
    ("updates", "code"),
    (
        ({"provider_id": _value("other")}, "OPENAI_PROVIDER_UNSUPPORTED"),
        ({"provider_id": _value(availability="unknown")}, "OPENAI_PROVIDER_UNSUPPORTED"),
        ({"model_id": _value("gpt-image-other")}, "OPENAI_MODEL_UNSUPPORTED"),
        ({"model_id": _value(availability="unknown")}, "OPENAI_MODEL_UNSUPPORTED"),
    ),
)
def test_only_the_frozen_openai_provider_and_model_are_supported(
    updates: dict[str, object], code: str
) -> None:
    report = ProviderOutputConfigurationBindingService().validate(_binding(), _configuration_report(**updates))

    assert report.status == "blocked"
    assert code in {finding.code for finding in report.findings}


def test_non_ready_upstream_configuration_fails_closed() -> None:
    upstream = _configuration_report().model_copy(update={"status": "blocked", "ready": False})

    report = ProviderOutputConfigurationBindingService().validate(_binding(), upstream)

    assert report.status == "blocked"
    assert [finding.code for finding in report.findings] == ["PROVIDER_CONFIGURATION_NOT_READY"]


def test_dtos_are_frozen_closed_and_safe_logical_references_are_required() -> None:
    binding = _binding()
    finding = ProviderOutputConfigurationFindingDTO(
        code="EXAMPLE", status="blocked", message="example"
    )

    with pytest.raises(ValidationError):
        ProviderOutputConfigurationBindingDTO(**binding.model_dump(), unexpected="value")
    missing_quality = binding.model_dump()
    del missing_quality["output_quality"]
    with pytest.raises(ValidationError):
        ProviderOutputConfigurationBindingDTO(**missing_quality)
    unsafe_reference = binding.model_dump()
    unsafe_reference["attempt_id"] = "C:\\unsafe"
    with pytest.raises(ValidationError):
        ProviderOutputConfigurationBindingDTO(**unsafe_reference)
    with pytest.raises(ValidationError):
        ProviderOutputConfigurationFindingDTO(
            code="EXAMPLE", status="blocked", message="example", provider_reference="https://unsafe"
        )
    with pytest.raises((ValidationError, FrozenInstanceError, TypeError)):
        binding.output_size = "1024x1024"  # type: ignore[misc]
    with pytest.raises((ValidationError, FrozenInstanceError, TypeError)):
        finding.code = "OTHER"  # type: ignore[misc]


def test_canonical_order_repeatability_nonmutation_and_redaction() -> None:
    binding = _binding(
        attempt_id="attempt:other",
        output_size="auto",
        output_quality="auto",
    )
    upstream = _configuration_report()
    before = (binding.model_dump(mode="json"), upstream.model_dump(mode="json"))
    service = ProviderOutputConfigurationBindingService()

    first = service.validate(binding, upstream)
    second = service.validate(binding, upstream)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert [finding.code for finding in first.findings] == sorted(
        finding.code for finding in first.findings
    )
    assert (binding.model_dump(mode="json"), upstream.model_dump(mode="json")) == before
    serialized = first.model_dump_json()
    for private_value in (
        "PRIVATE-PROMPT",
        "PRIVATE-API-KEY",
        "base64-image-bytes",
        "https://provider.invalid",
        "C:\\private\\image.png",
        "native exception detail",
    ):
        assert private_value not in serialized


def test_source_is_internal_and_has_no_transport_or_evidence_hand_off() -> None:
    source_path = (
        ROOT / "src/manga_director/production/next_generation_provider_output_configuration.py"
    )
    source = source_path.read_text(encoding="utf-8")
    for forbidden in (
        "next_generation_openai_provider_adapter",
        "next_generation_provider_adapter_composition",
        "GenerationEvidenceEnvelopeDTO",
        "GenerationConfigurationEvidenceDTO",
        "OpenAI(",
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
    assert "next_generation_provider_output_configuration" not in production_init
    assert "next_generation_provider_output_configuration" not in root_init
