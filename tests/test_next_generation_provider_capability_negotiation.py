"""Focused contracts for internal Provider Capability Negotiation validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_provider_capability_negotiation import (
    GenerationCapabilityRequirementDTO,
    ProviderCapabilityDeclarationDTO,
    ProviderCapabilityNegotiationService,
    ProviderCapabilityStateDTO,
)

ROOT = Path(__file__).resolve().parents[1]


def _requirement(capability_id: str, level: str = "required") -> GenerationCapabilityRequirementDTO:
    return GenerationCapabilityRequirementDTO(
        capability_id=capability_id, requirement_level=level
    )


def _state(capability_id: str, state: str = "supported") -> ProviderCapabilityStateDTO:
    return ProviderCapabilityStateDTO(capability_id=capability_id, state=state)


def _declaration(*states: ProviderCapabilityStateDTO) -> ProviderCapabilityDeclarationDTO:
    return ProviderCapabilityDeclarationDTO(
        provider_reference="provider:explicit", capability_states=states
    )


def _validate(
    requirements: tuple[GenerationCapabilityRequirementDTO, ...],
    *states: ProviderCapabilityStateDTO,
):
    return ProviderCapabilityNegotiationService().validate(requirements, _declaration(*states))


def test_dtos_are_frozen_closed_canonical_and_non_mutating() -> None:
    requirements = (_requirement("seed"), _requirement("text_prompt"))
    declaration = _declaration(_state("text_prompt"), _state("seed"))
    before = (tuple(item.model_dump() for item in requirements), declaration.model_dump())

    report = ProviderCapabilityNegotiationService().validate(requirements, declaration)

    with pytest.raises(ValidationError):
        requirements[0].capability_id = "dimensions"
    with pytest.raises(ValidationError):
        ProviderCapabilityStateDTO(capability_id="seed", state="supported", raw_prompt="private")
    assert tuple(item.capability_id for item in report.requirements) == ("seed", "text_prompt")
    assert tuple(item.capability_id for item in report.declaration.capability_states) == (
        "seed",
        "text_prompt",
    )
    assert (tuple(item.model_dump() for item in requirements), declaration.model_dump()) == before


def test_supported_is_satisfied_without_implicit_production_profile() -> None:
    report = _validate((_requirement("text_prompt"),), _state("text_prompt"))

    assert report.results[0].outcome == "satisfied"
    assert report.results[0].review_required is False
    assert report.status == "ready"
    assert report.requirements == (_requirement("text_prompt"),)


def test_missing_declaration_is_missing_and_requires_review_when_required() -> None:
    report = _validate((_requirement("provenance_capture"),))

    assert report.results[0].declared_state is None
    assert report.results[0].outcome == "missing"
    assert report.results[0].review_required is True
    assert report.status == "needs_review"


@pytest.mark.parametrize("state", ("unsupported", "unknown"))
def test_required_unsupported_or_unknown_requires_review(state: str) -> None:
    report = _validate((_requirement("seed"),), _state("seed", state))

    assert report.results[0].outcome == state
    assert report.results[0].review_required is True
    assert report.status == "needs_review"


@pytest.mark.parametrize("state", (None, "unsupported", "unknown"))
def test_optional_gap_is_a_warning_and_keeps_report_ready(state: str | None) -> None:
    states = () if state is None else (_state("reference_image_input", state),)
    report = _validate((_requirement("reference_image_input", "optional"),), *states)

    assert report.results[0].outcome == ("missing" if state is None else state)
    assert report.results[0].review_required is False
    assert report.status == "ready"
    assert report.findings[0].status == "warning"


def test_duplicate_requirement_is_blocked_without_merging() -> None:
    report = _validate((_requirement("seed"), _requirement("seed")), _state("seed"))

    assert "DUPLICATE_CAPABILITY_REQUIREMENT" in {item.code for item in report.findings}
    assert report.status == "blocked"


def test_duplicate_provider_declaration_is_blocked_without_merging() -> None:
    report = _validate((_requirement("seed"),), _state("seed"), _state("seed"))

    assert "DUPLICATE_PROVIDER_CAPABILITY_DECLARATION" in {item.code for item in report.findings}
    assert report.status == "blocked"


def test_conflicting_provider_declaration_is_blocked_without_selection() -> None:
    report = _validate(
        (_requirement("seed"),), _state("seed", "supported"), _state("seed", "unknown")
    )

    assert "CONFLICTING_PROVIDER_CAPABILITY_DECLARATION" in {item.code for item in report.findings}
    assert report.status == "blocked"


def test_canonical_ordering_and_unknown_non_inference() -> None:
    report = _validate(
        (_requirement("seed"), _requirement("dimensions", "optional")),
        _state("seed", "unknown"),
        _state("dimensions", "supported"),
    )

    assert tuple(item.capability_id for item in report.results) == ("dimensions", "seed")
    assert tuple(item.outcome for item in report.results) == ("satisfied", "unknown")
    assert report.status == "needs_review"


def test_closed_vocabulary_and_opaque_provider_reference_are_validated() -> None:
    with pytest.raises(ValidationError):
        _requirement("workflow_selection")
    with pytest.raises(ValidationError):
        ProviderCapabilityDeclarationDTO(provider_reference="https://provider", capability_states=())


def test_source_keeps_public_exports_and_all_side_effect_boundaries_out() -> None:
    source = (
        ROOT
        / "src/manga_director/production/next_generation_provider_capability_negotiation.py"
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
    ):
        assert forbidden not in source
    production_init = (ROOT / "src/manga_director/production/__init__.py").read_text(
        encoding="utf-8"
    )
    root_init = (ROOT / "src/manga_director/__init__.py").read_text(encoding="utf-8")
    assert "next_generation_provider_capability_negotiation" not in production_init
    assert "next_generation_provider_capability_negotiation" not in root_init
