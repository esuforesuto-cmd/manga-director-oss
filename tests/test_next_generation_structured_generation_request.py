"""Focused contracts for internal Structured Generation Request validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_generation_evidence import (
    GenerationIdentityBindingDTO,
    GenerationInputEvidenceDTO,
)
from manga_director.production.next_generation_provider_capability_negotiation import (
    GenerationCapabilityRequirementDTO,
)
from manga_director.production.next_generation_structured_generation_request import (
    GenerationProductionProfileDTO,
    StructuredGenerationRequestDTO,
    StructuredGenerationRequestValidationService,
)

ROOT = Path(__file__).resolve().parents[1]


def _requirement(capability_id: str, level: str = "required") -> GenerationCapabilityRequirementDTO:
    return GenerationCapabilityRequirementDTO(
        capability_id=capability_id, requirement_level=level
    )


def _binding(
    character_id: str = "character:aki",
    identity_id: str = "identity:aki:v1",
    identity_version: str = "v1",
    reference_asset_ids: tuple[str, ...] = ("asset:aki:front",),
) -> GenerationIdentityBindingDTO:
    return GenerationIdentityBindingDTO(
        character_id=character_id,
        identity_id=identity_id,
        identity_version=identity_version,
        reference_asset_ids=reference_asset_ids,
    )


def _profile(
    *requirements: GenerationCapabilityRequirementDTO,
    profile_id: str = "profile:manga",
    profile_version: str = "v1",
) -> GenerationProductionProfileDTO:
    return GenerationProductionProfileDTO(
        profile_id=profile_id,
        profile_version=profile_version,
        capability_requirements=requirements,
    )


def _request(
    profile: GenerationProductionProfileDTO,
    **updates: object,
) -> StructuredGenerationRequestDTO:
    values: dict[str, object] = {
        "request_id": "request:001",
        "target_page_reference": "page:001",
        "generation_intent_reference": "intent:001",
        "input": GenerationInputEvidenceDTO(input_reference="input:001"),
        "capability_requirements": profile.capability_requirements,
        "provenance_reference": "provenance:001",
        "profile_id": profile.profile_id,
        "profile_version": profile.profile_version,
    }
    values.update(updates)
    return StructuredGenerationRequestDTO(**values)


def _validate(request: StructuredGenerationRequestDTO, profile: GenerationProductionProfileDTO):
    return StructuredGenerationRequestValidationService().validate(request, profile)


def test_dtos_are_frozen_closed_and_reject_raw_prompt() -> None:
    profile = _profile(_requirement("text_prompt"))
    request = _request(profile)

    with pytest.raises(ValidationError):
        request.request_id = "request:changed"
    with pytest.raises(ValidationError):
        StructuredGenerationRequestDTO(**request.model_dump(), raw_prompt="private")
    with pytest.raises(ValidationError):
        GenerationProductionProfileDTO(**profile.model_dump(), metadata={})


def test_logical_references_are_validated_and_target_panel_is_optional() -> None:
    profile = _profile(_requirement("text_prompt"))
    request = _request(profile, target_panel_reference=None)

    assert _validate(request, profile).status == "ready"
    with pytest.raises(ValidationError):
        _request(profile, generation_intent_reference="https://private")


def test_profile_snapshot_fields_are_required() -> None:
    profile = _profile(_requirement("text_prompt"))
    values = _request(profile).model_dump()
    values.pop("profile_id")

    with pytest.raises(ValidationError):
        StructuredGenerationRequestDTO(**values)


def test_exact_profile_projection_and_ordering_difference_pass() -> None:
    profile = _profile(_requirement("text_prompt"), _requirement("seed", "optional"))
    request = _request(
        profile,
        capability_requirements=(_requirement("seed", "optional"), _requirement("text_prompt")),
    )

    report = _validate(request, profile)

    assert report.status == "ready"
    assert tuple(item.capability_id for item in report.profile.capability_requirements) == (
        "seed",
        "text_prompt",
    )
    assert report.request.capability_requirements == report.profile.capability_requirements


def test_profile_snapshot_or_projection_mismatch_is_blocked() -> None:
    profile = _profile(_requirement("text_prompt"))
    version_mismatch = _validate(_request(profile, profile_version="v2"), profile)
    requirement_mismatch = _validate(_request(profile, capability_requirements=(_requirement("seed"),)), profile)

    assert "PROFILE_SNAPSHOT_MISMATCH" in {item.code for item in version_mismatch.findings}
    assert "PROFILE_REQUIREMENT_PROJECTION_MISMATCH" in {
        item.code for item in requirement_mismatch.findings
    }


def test_profile_and_request_requirement_duplicates_are_blocked() -> None:
    profile_duplicate = _profile(_requirement("seed"), _requirement("seed"))
    request_duplicate_profile = _request(profile_duplicate)
    profile = _profile(_requirement("seed"))
    request_duplicate = _request(profile, capability_requirements=(_requirement("seed"), _requirement("seed")))

    profile_report = _validate(request_duplicate_profile, profile_duplicate)
    request_report = _validate(request_duplicate, profile)

    assert "DUPLICATE_PROFILE_CAPABILITY_REQUIREMENT" in {
        item.code for item in profile_report.findings
    }
    assert "DUPLICATE_REQUEST_CAPABILITY_REQUIREMENT" in {
        item.code for item in request_report.findings
    }


def test_duplicate_identity_binding_and_preservation_scope_are_blocked() -> None:
    profile = _profile(_requirement("identity_reference_preservation"))
    request = _request(
        profile,
        identity_bindings=(_binding(), _binding()),
        preservation_scopes=("seed", "seed"),
    )

    report = _validate(request, profile)

    assert {"DUPLICATE_IDENTITY_BINDING", "DUPLICATE_PRESERVATION_SCOPE"} <= {
        item.code for item in report.findings
    }
    assert report.status == "blocked"


def test_identity_references_and_preservation_scopes_are_canonical_non_mutating_and_deterministic() -> None:
    profile = _profile(_requirement("identity_reference_preservation"), _requirement("seed"))
    first = _binding(
        character_id="character:z",
        identity_id="identity:z:v1",
        reference_asset_ids=("asset:z:side", "asset:z:front"),
    )
    second = _binding(
        character_id="character:a",
        identity_id="identity:a:v1",
        reference_asset_ids=("asset:a:side", "asset:a:front"),
    )
    request = _request(
        profile,
        identity_bindings=(first, second),
        preservation_scopes=("seed", "identity_bindings"),
        capability_requirements=(_requirement("seed"), _requirement("identity_reference_preservation")),
    )
    before = (request.model_dump(mode="json"), profile.model_dump(mode="json"))

    first_report = _validate(request, profile)
    second_report = _validate(request, profile)

    assert tuple(item.character_id for item in first_report.request.identity_bindings) == (
        "character:a",
        "character:z",
    )
    assert first_report.request.identity_bindings[0].reference_asset_ids == (
        "asset:a:front",
        "asset:a:side",
    )
    assert first_report.request.preservation_scopes == ("identity_bindings", "seed")
    assert (request.model_dump(mode="json"), profile.model_dump(mode="json")) == before
    assert first_report.model_dump(mode="json") == second_report.model_dump(mode="json")


def test_source_excludes_public_exports_execution_and_io_boundaries() -> None:
    source = (
        ROOT
        / "src/manga_director/production/next_generation_structured_generation_request.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "manga_director.adapters",
        "manga_director.agents",
        "manga_director.plugins",
        "manga_director.workflow",
        "manga_director.domain.state_machine",
        ".execute(",
        ".generate(",
        "open(",
        "read_text(",
        "requests.",
        "httpx.",
        "hashlib",
    ):
        assert forbidden not in source
    production_init = (ROOT / "src/manga_director/production/__init__.py").read_text(
        encoding="utf-8"
    )
    root_init = (ROOT / "src/manga_director/__init__.py").read_text(encoding="utf-8")
    assert "next_generation_structured_generation_request" not in production_init
    assert "next_generation_structured_generation_request" not in root_init
