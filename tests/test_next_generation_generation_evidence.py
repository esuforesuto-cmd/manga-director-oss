"""Contracts for internal caller-supplied Generation Evidence validation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_generation_evidence import (
    EvidenceValueDTO,
    GenerationConfigurationEvidenceDTO,
    GenerationEvidenceEnvelopeDTO,
    GenerationEvidenceValidationService,
    GenerationIdentityBindingDTO,
    GenerationInputEvidenceDTO,
    GenerationOutputEvidenceDTO,
    GenerationParameterEvidenceDTO,
    ProviderSpecificEvidenceDTO,
)

ROOT = Path(__file__).resolve().parents[1]


def _known(value: str | int | float | bool) -> EvidenceValueDTO:
    return EvidenceValueDTO(availability="known", value=value)


def _unknown() -> EvidenceValueDTO:
    return EvidenceValueDTO(availability="unknown")


def _configuration(
    *,
    parameters: tuple[GenerationParameterEvidenceDTO, ...] = (),
    provider_specific: tuple[ProviderSpecificEvidenceDTO, ...] = (),
) -> GenerationConfigurationEvidenceDTO:
    return GenerationConfigurationEvidenceDTO(
        provider_id=_known("mock"),
        model_id=_known("mock-image"),
        model_version=_unknown(),
        workflow_id=_known("workflow:page"),
        workflow_version=_unknown(),
        seed=_unknown(),
        parameters=parameters,
        provider_specific_evidence=provider_specific,
    )


def _envelope(
    *,
    attempt_id: str = "attempt:001",
    output_asset_id: str = "asset:generated:001",
    output_hash: EvidenceValueDTO | None = None,
    provenance: str = "workflow:generated",
    configuration: GenerationConfigurationEvidenceDTO | None = None,
    bindings: tuple[GenerationIdentityBindingDTO, ...] = (),
) -> GenerationEvidenceEnvelopeDTO:
    return GenerationEvidenceEnvelopeDTO(
        attempt_id=attempt_id,
        observed_at=datetime(2026, 8, 21, 0, 0, tzinfo=UTC),
        provenance_reference=provenance,
        input=GenerationInputEvidenceDTO(input_reference="artifact:prompt:001"),
        output=GenerationOutputEvidenceDTO(
            output_asset_id=output_asset_id,
            output_content_hash=output_hash,
            media_type="image/png",
        ),
        configuration=configuration or _configuration(),
        identity_bindings=bindings,
    )


def test_dtos_are_frozen_closed_and_evidence_values_preserve_their_declared_state() -> None:
    envelope = _envelope()

    with pytest.raises(ValidationError):
        envelope.attempt_id = "attempt:changed"
    with pytest.raises(ValidationError):
        GenerationInputEvidenceDTO(input_reference="artifact:prompt", prompt="# raw prompt")
    with pytest.raises(ValidationError):
        EvidenceValueDTO(availability="known")
    with pytest.raises(ValidationError):
        EvidenceValueDTO(availability="unknown", value="guessed")
    with pytest.raises(ValidationError):
        EvidenceValueDTO(availability="unavailable", value="provider-value")

    assert _unknown().availability == "unknown"
    assert EvidenceValueDTO(availability="unavailable").availability == "unavailable"


def test_validation_is_canonical_and_preserves_caller_input() -> None:
    binding = GenerationIdentityBindingDTO(
        character_id="character:aki",
        identity_id="identity:aki:v1",
        identity_version="v1",
        reference_asset_ids=("asset:face", "asset:body"),
    )
    configuration = _configuration(
        parameters=(
            GenerationParameterEvidenceDTO(key="width", value=_known(1024)),
            GenerationParameterEvidenceDTO(key="height", value=_known(1536)),
        ),
        provider_specific=(
            ProviderSpecificEvidenceDTO(namespace="mock", key="style", value=_known("line")),
            ProviderSpecificEvidenceDTO(namespace="mock", key="sampler", value=_known("test")),
        ),
    )
    second = _envelope(attempt_id="attempt:002", configuration=configuration, bindings=(binding,))
    first = _envelope(attempt_id="attempt:001")
    supplied = (second, first)
    before = tuple(envelope.model_dump(mode="json") for envelope in supplied)

    report = GenerationEvidenceValidationService().validate(supplied)

    assert tuple(envelope.attempt_id for envelope in report.envelopes) == ("attempt:001", "attempt:002")
    assert tuple(item.key for item in report.envelopes[1].configuration.parameters) == (
        "height",
        "width",
    )
    assert tuple(item.key for item in report.envelopes[1].configuration.provider_specific_evidence) == (
        "sampler",
        "style",
    )
    assert report.envelopes[1].identity_bindings[0].reference_asset_ids == (
        "asset:body",
        "asset:face",
    )
    assert tuple(envelope.model_dump(mode="json") for envelope in supplied) == before
    assert report.status == "needs_evidence"
    assert report.content_hash_calculated is False
    assert report.timestamp_generated is False


def test_duplicate_attempt_identity_parameter_and_provider_evidence_are_blocked() -> None:
    binding = GenerationIdentityBindingDTO(
        character_id="character:aki",
        identity_id="identity:aki:v1",
        identity_version="v1",
    )
    parameter = GenerationParameterEvidenceDTO(key="width", value=_known(1024))
    provider_evidence = ProviderSpecificEvidenceDTO(
        namespace="mock", key="sampler", value=_known("test")
    )
    report = GenerationEvidenceValidationService().validate(
        (
            _envelope(
                configuration=_configuration(
                    parameters=(parameter, parameter),
                    provider_specific=(provider_evidence, provider_evidence),
                ),
                bindings=(binding, binding),
            ),
            _envelope(),
        )
    )

    assert report.status == "blocked"
    assert tuple(finding.code for finding in report.findings if finding.status == "blocked") == (
        "duplicate_attempt_id",
        "duplicate_identity_binding",
        "duplicate_parameter_key",
        "duplicate_provider_specific_evidence",
    )


def test_conflicting_caller_supplied_output_hash_and_provenance_are_blocked() -> None:
    report = GenerationEvidenceValidationService().validate(
        (
            _envelope(output_hash=_known("hash-a"), provenance="workflow:one"),
            _envelope(
                attempt_id="attempt:002",
                output_hash=_known("hash-b"),
                provenance="workflow:two",
            ),
        )
    )

    assert report.status == "blocked"
    assert tuple(finding.code for finding in report.findings) == (
        "conflicting_output_content_hash",
        "conflicting_output_provenance",
        "unknown_evidence",
        "unknown_evidence",
        "unknown_evidence",
        "unknown_evidence",
        "unknown_evidence",
        "unknown_evidence",
    )


def test_unknown_and_unavailable_evidence_are_not_inferred() -> None:
    configuration = GenerationConfigurationEvidenceDTO(
        provider_id=EvidenceValueDTO(availability="unavailable"),
        model_id=_unknown(),
        model_version=EvidenceValueDTO(availability="unavailable"),
        workflow_id=_unknown(),
        workflow_version=_unknown(),
        seed=_unknown(),
    )

    report = GenerationEvidenceValidationService().validate((_envelope(configuration=configuration),))

    assert report.status == "needs_evidence"
    assert tuple((finding.code, finding.evidence_name) for finding in report.findings) == (
        ("unavailable_evidence", "model_version"),
        ("unavailable_evidence", "provider_id"),
        ("unknown_evidence", "model_id"),
        ("unknown_evidence", "seed"),
        ("unknown_evidence", "workflow_id"),
        ("unknown_evidence", "workflow_version"),
    )


def test_identity_binding_requires_an_explicit_version_and_never_selects_one() -> None:
    with pytest.raises(ValidationError):
        GenerationIdentityBindingDTO(
            character_id="character:aki",
            identity_id="identity:aki:v1",
            identity_version="",
        )

    report = GenerationEvidenceValidationService().validate(
        (
            _envelope(
                bindings=(
                    GenerationIdentityBindingDTO(
                        character_id="character:aki",
                        identity_id="identity:aki:v1",
                        identity_version="v1",
                    ),
                    GenerationIdentityBindingDTO(
                        character_id="character:aki",
                        identity_id="identity:aki:v2",
                        identity_version="v2",
                    ),
                )
            ),
        )
    )

    assert report.identity_version_selected is False
    assert "selected_version" not in type(report).model_fields
    assert "latest_version" not in type(report).model_fields


def test_provider_specific_evidence_rejects_secrets_and_raw_payloads_without_leaking_values() -> None:
    with pytest.raises(ValidationError, match="not allowed"):
        ProviderSpecificEvidenceDTO(namespace="openai", key="api_key", value=_known("secret-value"))
    with pytest.raises(ValidationError):
        ProviderSpecificEvidenceDTO(
            namespace="openai",
            key="sampler",
            value=_known("safe"),
            raw_response={"token": "secret-value"},
        )
    with pytest.raises(ValidationError):
        EvidenceValueDTO(availability="known", value={"nested": "payload"})


def test_timestamp_is_caller_supplied_and_timezone_aware() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        GenerationEvidenceEnvelopeDTO(
            attempt_id="attempt:naive",
            observed_at=datetime(2026, 8, 21, 0, 0),
            provenance_reference="workflow:generated",
            input=GenerationInputEvidenceDTO(input_reference="artifact:prompt:001"),
            output=GenerationOutputEvidenceDTO(output_asset_id="asset:generated:001"),
            configuration=_configuration(),
        )


def test_report_has_no_reproducibility_claim_and_source_keeps_boundaries_out() -> None:
    report = GenerationEvidenceValidationService().validate((_envelope(),))
    source = (
        ROOT / "src/manga_director/production/next_generation_generation_evidence.py"
    ).read_text(encoding="utf-8")

    for field_name in ("reproducible", "is_reproducible", "reproducibility_score"):
        assert field_name not in type(report).model_fields
    for forbidden in (
        "manga_director.api",
        "manga_director.cli",
        "manga_director.mcp",
        "manga_director.repositories",
        "manga_director.workflow",
        "manga_director.providers",
        ".execute(",
        ".advance(",
        "datetime.now",
        "hashlib",
        "open(",
        "read_text(",
        "requests.",
        "httpx.",
        "save(",
        ".load(",
    ):
        assert forbidden not in source
