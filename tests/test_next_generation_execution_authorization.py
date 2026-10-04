"""Focused contracts for internal execution authorization validation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_execution_authorization import (
    ExecutionAuthorizationRecordDTO,
    ExecutionAuthorizationValidationService,
)
from manga_director.production.next_generation_generation_evidence import GenerationInputEvidenceDTO
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


def _readiness(
    *requirements: GenerationCapabilityRequirementDTO,
    states: tuple[ProviderCapabilityStateDTO, ...] = (),
    request_requirements: tuple[GenerationCapabilityRequirementDTO, ...] | None = None,
    provider_reference: str = "provider:local-a",
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
        capability_requirements=request_requirements or requirements,
        provenance_reference="provenance:001",
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
    )
    request_report = StructuredGenerationRequestValidationService().validate(request, profile)
    negotiation_report = ProviderCapabilityNegotiationService().validate(
        request.capability_requirements,
        ProviderCapabilityDeclarationDTO(
            provider_reference=provider_reference,
            capability_states=states,
        ),
    )
    return PreExecutionReadinessService().validate(
        PreExecutionReadinessInputDTO(
            request_validation_report=request_report,
            capability_negotiation_report=negotiation_report,
            provider_reference=provider_reference,
        )
    )


def _record(
    authorization_id: str = "authorization:001",
    authorizer_id: str = "human:editor-a",
    request_id: str = "request:001",
    provider_reference: str = "provider:local-a",
    rationale_reference: str | None = None,
) -> ExecutionAuthorizationRecordDTO:
    return ExecutionAuthorizationRecordDTO(
        authorization_id=authorization_id,
        authorizer_id=authorizer_id,
        authorized_at=datetime(2026, 8, 21, 12, 0, tzinfo=UTC),
        request_id=request_id,
        provider_reference=provider_reference,
        rationale_reference=rationale_reference,
    )


def _validate(readiness, *records: ExecutionAuthorizationRecordDTO):
    return ExecutionAuthorizationValidationService().validate(readiness, records)


def test_record_is_frozen_closed_timezone_aware_and_reference_safe() -> None:
    record = _record()

    with pytest.raises(ValidationError):
        record.authorizer_id = "human:editor-b"
    with pytest.raises(ValidationError):
        ExecutionAuthorizationRecordDTO(**record.model_dump(), raw_rationale="private")
    with pytest.raises(ValidationError):
        _record(rationale_reference="https://private")
    with pytest.raises(ValidationError):
        ExecutionAuthorizationRecordDTO(
            **record.model_dump(exclude={"authorized_at"}),
            authorized_at=datetime(2026, 8, 21, 12, 0),
        )


def test_valid_bound_record_returns_ready() -> None:
    readiness = _readiness(_requirement("text_prompt"), states=(ProviderCapabilityStateDTO(capability_id="text_prompt", state="supported"),))

    report = _validate(readiness, _record(rationale_reference="rationale:001"))

    assert report.status == "ready"
    assert report.ready is True
    assert report.findings == ()


def test_missing_authorization_needs_review() -> None:
    readiness = _readiness()

    report = _validate(readiness)

    assert report.status == "needs_review"
    assert report.ready is False
    assert [item.code for item in report.findings] == ["MISSING_EXECUTION_AUTHORIZATION"]


def test_readiness_needs_review_cannot_be_overridden() -> None:
    readiness = _readiness(
        _requirement("seed"),
        states=(ProviderCapabilityStateDTO(capability_id="seed", state="unknown"),),
    )

    report = _validate(readiness, _record())

    assert readiness.status == "needs_review"
    assert report.status == "needs_review"
    assert report.ready is False
    assert [item.code for item in report.findings] == ["READINESS_NEEDS_REVIEW"]


def test_readiness_blocked_cannot_be_overridden() -> None:
    readiness = _readiness(
        _requirement("text_prompt"),
        request_requirements=(_requirement("seed"),),
    )

    report = _validate(readiness, _record())

    assert readiness.status == "blocked"
    assert report.status == "blocked"
    assert report.ready is False
    assert "READINESS_BLOCKED" in {item.code for item in report.findings}


def test_multiple_distinct_authorizers_are_allowed_and_canonical() -> None:
    readiness = _readiness()
    second = _record(
        authorization_id="authorization:002",
        authorizer_id="human:editor-b",
    )

    report = _validate(readiness, second, _record())

    assert report.status == "ready"
    assert tuple(item.authorizer_id for item in report.authorizations) == (
        "human:editor-a",
        "human:editor-b",
    )


def test_duplicate_authorization_id_is_blocked() -> None:
    readiness = _readiness()

    report = _validate(
        readiness,
        _record(),
        _record(authorization_id="authorization:001", authorizer_id="human:editor-b"),
    )

    assert report.status == "blocked"
    assert "DUPLICATE_AUTHORIZATION_ID" in {item.code for item in report.findings}


def test_duplicate_same_authorizer_request_provider_is_blocked() -> None:
    readiness = _readiness()

    report = _validate(
        readiness,
        _record(),
        _record(authorization_id="authorization:002"),
    )

    assert report.status == "blocked"
    assert "DUPLICATE_AUTHORIZER_REQUEST_PROVIDER" in {item.code for item in report.findings}


def test_request_and_provider_mismatches_are_blocked() -> None:
    readiness = _readiness()

    report = _validate(
        readiness,
        _record(request_id="request:other", provider_reference="provider:other"),
    )

    assert report.status == "blocked"
    assert {"AUTHORIZATION_REQUEST_MISMATCH", "AUTHORIZATION_PROVIDER_MISMATCH"} <= {
        item.code for item in report.findings
    }


def test_input_is_non_mutating_and_repeated_results_are_deterministic() -> None:
    readiness = _readiness()
    records = (
        _record(authorization_id="authorization:002", authorizer_id="human:editor-b"),
        _record(),
    )
    before = (readiness.model_dump(mode="json"), tuple(item.model_dump(mode="json") for item in records))

    first = _validate(readiness, *records)
    second = _validate(readiness, *records)

    assert (readiness.model_dump(mode="json"), tuple(item.model_dump(mode="json") for item in records)) == before
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_source_keeps_public_exports_and_side_effect_boundaries_out() -> None:
    source = (
        ROOT
        / "src/manga_director/production/next_generation_execution_authorization.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "manga_director.adapters",
        "manga_director.agents",
        "manga_director.plugins",
        "manga_director.workflow",
        "manga_director.domain.state_machine",
        "manga_director.security",
        "GenerationEvidenceEnvelopeDTO",
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
    assert "next_generation_execution_authorization" not in production_init
    assert "next_generation_execution_authorization" not in root_init
