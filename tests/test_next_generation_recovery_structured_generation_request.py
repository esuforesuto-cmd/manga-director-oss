"""Focused contracts for internal Recovery Structured Generation Request validation."""

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
from manga_director.production.next_generation_recovery_structured_generation_request import (
    RecoveryStructuredGenerationRequestDTO,
    RecoveryStructuredGenerationRequestValidationService,
)
from manga_director.production.next_generation_structured_generation_request import (
    GenerationProductionProfileDTO,
)

ROOT = Path(__file__).resolve().parents[1]


def _requirement(capability_id: str, level: str = "required") -> GenerationCapabilityRequirementDTO:
    return GenerationCapabilityRequirementDTO(
        capability_id=capability_id,
        requirement_level=level,
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
    profile_id: str = "profile:recovery",
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
) -> RecoveryStructuredGenerationRequestDTO:
    values: dict[str, object] = {
        "recovery_request_id": "recovery-request:001",
        "recovery_proposal_id": "proposal:001",
        "generation_intent_reference": "recovery-intent:001",
        "input": GenerationInputEvidenceDTO(input_reference="recovery-input:001"),
        "profile_id": profile.profile_id,
        "profile_version": profile.profile_version,
        "capability_requirements": profile.capability_requirements,
        "identity_bindings": (_binding(),),
    }
    values.update(updates)
    return RecoveryStructuredGenerationRequestDTO(**values)


def _validate(
    request: RecoveryStructuredGenerationRequestDTO,
    profile: GenerationProductionProfileDTO,
):
    return RecoveryStructuredGenerationRequestValidationService().validate(request, profile)


def test_dtos_are_frozen_closed_and_require_nonempty_explicit_identity_bindings() -> None:
    profile = _profile(_requirement("text_prompt"))
    request = _request(profile)

    with pytest.raises(ValidationError):
        request.recovery_request_id = "recovery-request:changed"
    with pytest.raises(ValidationError):
        RecoveryStructuredGenerationRequestDTO(**request.model_dump(), raw_prompt="private")
    with pytest.raises(ValidationError):
        _request(profile, recovery_proposal_id="https://proposal")
    with pytest.raises(ValidationError):
        _request(profile, identity_bindings=())


def test_exact_profile_projection_and_requirement_ordering_pass() -> None:
    profile = _profile(_requirement("text_prompt"), _requirement("seed", "optional"))
    request = _request(
        profile,
        capability_requirements=(_requirement("seed", "optional"), _requirement("text_prompt")),
    )

    report = _validate(request, profile)

    assert report.status == "ready"
    assert report.request.capability_requirements == report.profile.capability_requirements


def test_profile_snapshot_and_projection_mismatches_are_blocked() -> None:
    profile = _profile(_requirement("text_prompt"))
    version_mismatch = _validate(_request(profile, profile_version="v2"), profile)
    requirement_mismatch = _validate(
        _request(profile, capability_requirements=(_requirement("seed"),)),
        profile,
    )

    assert "PROFILE_SNAPSHOT_MISMATCH" in {item.code for item in version_mismatch.findings}
    assert "PROFILE_REQUIREMENT_PROJECTION_MISMATCH" in {
        item.code for item in requirement_mismatch.findings
    }


def test_duplicate_profile_and_request_requirements_are_blocked() -> None:
    profile_duplicate = _profile(_requirement("seed"), _requirement("seed"))
    profile = _profile(_requirement("seed"))

    duplicate_profile = _validate(_request(profile_duplicate), profile_duplicate)
    duplicate_request = _validate(
        _request(profile, capability_requirements=(_requirement("seed"), _requirement("seed"))),
        profile,
    )

    assert "DUPLICATE_PROFILE_CAPABILITY_REQUIREMENT" in {
        item.code for item in duplicate_profile.findings
    }
    assert "DUPLICATE_RECOVERY_REQUEST_CAPABILITY_REQUIREMENT" in {
        item.code for item in duplicate_request.findings
    }


def test_duplicate_identity_bindings_are_blocked() -> None:
    profile = _profile(_requirement("identity_reference_preservation"))

    report = _validate(_request(profile, identity_bindings=(_binding(), _binding())), profile)

    assert "DUPLICATE_IDENTITY_BINDING" in {item.code for item in report.findings}


def test_canonical_identity_ordering_is_non_mutating_and_deterministic() -> None:
    profile = _profile(_requirement("identity_reference_preservation"), _requirement("seed"))
    request = _request(
        profile,
        capability_requirements=(_requirement("seed"), _requirement("identity_reference_preservation")),
        identity_bindings=(
            _binding(
                character_id="character:z",
                identity_id="identity:z:v1",
                reference_asset_ids=("asset:z:side", "asset:z:front"),
            ),
            _binding(
                character_id="character:a",
                identity_id="identity:a:v1",
                reference_asset_ids=("asset:a:side", "asset:a:front"),
            ),
        ),
    )
    before = (request.model_dump(mode="json"), profile.model_dump(mode="json"))

    first = _validate(request, profile)
    second = _validate(request, profile)

    assert tuple(item.character_id for item in first.request.identity_bindings) == (
        "character:a",
        "character:z",
    )
    assert first.request.identity_bindings[0].reference_asset_ids == (
        "asset:a:front",
        "asset:a:side",
    )
    assert (request.model_dump(mode="json"), profile.model_dump(mode="json")) == before
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_source_excludes_proposal_duplication_provider_execution_and_public_exports() -> None:
    source = (
        ROOT
        / "src/manga_director/production/next_generation_recovery_structured_generation_request.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "next_generation_generation_recovery_proposal",
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
        "hashlib",
    ):
        assert forbidden not in source
    production_init = (ROOT / "src/manga_director/production/__init__.py").read_text(
        encoding="utf-8"
    )
    root_init = (ROOT / "src/manga_director/__init__.py").read_text(encoding="utf-8")
    assert "next_generation_recovery_structured_generation_request" not in production_init
    assert "next_generation_recovery_structured_generation_request" not in root_init
