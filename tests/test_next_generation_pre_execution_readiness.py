"""Focused contracts for internal Pre-Execution Readiness validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_generation_evidence import (
    GenerationIdentityBindingDTO,
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
from manga_director.production.next_generation_structured_generation_request import (
    GenerationProductionProfileDTO,
    StructuredGenerationRequestDTO,
    StructuredGenerationRequestValidationService,
)

ROOT = Path(__file__).resolve().parents[1]


def _requirement(capability_id: str, level: str = "required") -> GenerationCapabilityRequirementDTO:
    return GenerationCapabilityRequirementDTO(
        capability_id=capability_id,
        requirement_level=level,
    )


def _state(capability_id: str, state: str) -> ProviderCapabilityStateDTO:
    return ProviderCapabilityStateDTO(capability_id=capability_id, state=state)


def _request_report(
    *requirements: GenerationCapabilityRequirementDTO,
    identity_bindings: tuple[GenerationIdentityBindingDTO, ...] = (),
    preservation_scopes: tuple[str, ...] = (),
):
    profile = GenerationProductionProfileDTO(
        profile_id="profile:manga",
        profile_version="v1",
        capability_requirements=requirements,
    )
    request = StructuredGenerationRequestDTO(
        request_id="request:001",
        target_page_reference="page:001",
        generation_intent_reference="intent:001",
        input=GenerationInputEvidenceDTO(input_reference="input:001"),
        capability_requirements=requirements,
        provenance_reference="provenance:001",
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        identity_bindings=identity_bindings,
        preservation_scopes=preservation_scopes,
    )
    return StructuredGenerationRequestValidationService().validate(request, profile)


def _negotiation_report(
    requirements: tuple[GenerationCapabilityRequirementDTO, ...],
    *states: ProviderCapabilityStateDTO,
    provider_reference: str = "provider:local-a",
):
    declaration = ProviderCapabilityDeclarationDTO(
        provider_reference=provider_reference,
        capability_states=states,
    )
    return ProviderCapabilityNegotiationService().validate(requirements, declaration)


def _validate(
    request_report,
    negotiation_report,
    provider_reference: str = "provider:local-a",
):
    return PreExecutionReadinessService().validate(
        PreExecutionReadinessInputDTO(
            request_validation_report=request_report,
            capability_negotiation_report=negotiation_report,
            provider_reference=provider_reference,
        )
    )


def test_dtos_are_frozen_closed_and_validate_logical_provider_reference() -> None:
    request_report = _request_report(_requirement("text_prompt"))
    negotiation_report = _negotiation_report(
        (_requirement("text_prompt"),),
        _state("text_prompt", "supported"),
    )
    readiness_input = PreExecutionReadinessInputDTO(
        request_validation_report=request_report,
        capability_negotiation_report=negotiation_report,
        provider_reference="provider:local-a",
    )

    with pytest.raises(ValidationError):
        readiness_input.provider_reference = "provider:changed"
    with pytest.raises(ValidationError):
        PreExecutionReadinessInputDTO(
            **readiness_input.model_dump(exclude={"provider_reference"}),
            provider_reference="https://provider",
        )
    with pytest.raises(ValidationError):
        PreExecutionReadinessInputDTO(**readiness_input.model_dump(), raw_prompt="private")


def test_ready_requires_canonical_requirement_and_provider_binding() -> None:
    request_report = _request_report(
        _requirement("text_prompt"),
        _requirement("seed", "optional"),
    )
    negotiation_report = _negotiation_report(
        (_requirement("seed", "optional"), _requirement("text_prompt")),
        _state("text_prompt", "supported"),
        _state("seed", "supported"),
    )

    report = _validate(request_report, negotiation_report)

    assert report.status == "ready"
    assert report.ready is True
    assert report.findings == ()


def test_blocked_findings_cover_input_integrity_and_binding_failures() -> None:
    profile = GenerationProductionProfileDTO(
        profile_id="profile:manga",
        profile_version="v1",
        capability_requirements=(_requirement("text_prompt"),),
    )
    blocked_request = StructuredGenerationRequestValidationService().validate(
        StructuredGenerationRequestDTO(
            request_id="request:001",
            target_page_reference="page:001",
            generation_intent_reference="intent:001",
            input=GenerationInputEvidenceDTO(input_reference="input:001"),
            capability_requirements=(_requirement("seed"),),
            provenance_reference="provenance:001",
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
        ),
        profile,
    )
    blocked_negotiation = _negotiation_report(
        (_requirement("text_prompt"), _requirement("text_prompt")),
        _state("text_prompt", "supported"),
        _state("text_prompt", "supported"),
        provider_reference="provider:local-b",
    )

    report = _validate(blocked_request, blocked_negotiation)

    assert report.status == "blocked"
    assert report.ready is False
    assert {
        "REQUEST_VALIDATION_BLOCKED",
        "CAPABILITY_NEGOTIATION_BLOCKED",
        "REQUEST_NEGOTIATION_REQUIREMENT_MISMATCH",
        "PROVIDER_REFERENCE_MISMATCH",
    } <= {item.code for item in report.findings}


@pytest.mark.parametrize(
    ("state", "code"),
    ((None, "REQUIRED_CAPABILITY_MISSING"), ("unsupported", "REQUIRED_CAPABILITY_UNSUPPORTED"), ("unknown", "REQUIRED_CAPABILITY_UNKNOWN")),
)
def test_required_capability_gaps_need_review(state: str | None, code: str) -> None:
    request_report = _request_report(_requirement("seed"))
    states = () if state is None else (_state("seed", state),)
    negotiation_report = _negotiation_report((_requirement("seed"),), *states)

    report = _validate(request_report, negotiation_report)

    assert report.status == "needs_review"
    assert report.ready is False
    assert [(item.code, item.status) for item in report.findings] == [(code, "needs_review")]


@pytest.mark.parametrize(
    ("state", "code"),
    ((None, "OPTIONAL_CAPABILITY_MISSING"), ("unsupported", "OPTIONAL_CAPABILITY_UNSUPPORTED"), ("unknown", "OPTIONAL_CAPABILITY_UNKNOWN")),
)
def test_optional_capability_gaps_warn_but_keep_ready(state: str | None, code: str) -> None:
    request_report = _request_report(_requirement("seed", "optional"))
    states = () if state is None else (_state("seed", state),)
    negotiation_report = _negotiation_report((_requirement("seed", "optional"),), *states)

    report = _validate(request_report, negotiation_report)

    assert report.status == "ready"
    assert report.ready is True
    assert [(item.code, item.status) for item in report.findings] == [(code, "warning")]


def test_identity_bindings_and_preservation_scopes_do_not_create_requirements() -> None:
    identity_binding = GenerationIdentityBindingDTO(
        character_id="character:aki",
        identity_id="identity:aki:v1",
        identity_version="v1",
        reference_asset_ids=("asset:aki:front",),
    )
    request_report = _request_report(
        identity_bindings=(identity_binding,),
        preservation_scopes=("identity_bindings", "reference_asset_ids", "seed"),
    )
    negotiation_report = _negotiation_report(())

    report = _validate(request_report, negotiation_report)

    assert report.status == "ready"
    assert report.findings == ()


def test_input_is_non_mutating_and_reports_are_deterministic() -> None:
    request_report = _request_report(
        _requirement("text_prompt"),
        _requirement("seed", "optional"),
    )
    negotiation_report = _negotiation_report(
        (_requirement("seed", "optional"), _requirement("text_prompt")),
        _state("seed", "unknown"),
        _state("text_prompt", "supported"),
    )
    readiness_input = PreExecutionReadinessInputDTO(
        request_validation_report=request_report,
        capability_negotiation_report=negotiation_report,
        provider_reference="provider:local-a",
    )
    before = readiness_input.model_dump(mode="json")

    first = PreExecutionReadinessService().validate(readiness_input)
    second = PreExecutionReadinessService().validate(readiness_input)

    assert readiness_input.model_dump(mode="json") == before
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert [(item.code, item.status) for item in first.findings] == [
        ("OPTIONAL_CAPABILITY_UNKNOWN", "warning")
    ]


def test_source_keeps_public_exports_and_side_effect_boundaries_out() -> None:
    source = (
        ROOT
        / "src/manga_director/production/next_generation_pre_execution_readiness.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "manga_director.adapters",
        "manga_director.agents",
        "manga_director.plugins",
        "manga_director.workflow",
        "manga_director.domain.state_machine",
        "ProviderCapabilityNegotiationService",
        "GenerationEvidenceEnvelopeDTO",
        ".execute(",
        ".generate(",
        "open(",
        "read_text(",
        "requests.",
        "httpx.",
        "datetime",
    ):
        assert forbidden not in source
    production_init = (ROOT / "src/manga_director/production/__init__.py").read_text(
        encoding="utf-8"
    )
    root_init = (ROOT / "src/manga_director/__init__.py").read_text(encoding="utf-8")
    assert "next_generation_pre_execution_readiness" not in production_init
    assert "next_generation_pre_execution_readiness" not in root_init
