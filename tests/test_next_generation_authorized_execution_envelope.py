"""Focused contracts for internal authorized execution envelope validation."""

from __future__ import annotations

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


def _authorization_report(*, multiple_authorizers: bool = False):
    requirements = (_requirement("text_prompt"),)
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
    )
    request_report = StructuredGenerationRequestValidationService().validate(request, profile)
    negotiation_report = ProviderCapabilityNegotiationService().validate(
        requirements,
        ProviderCapabilityDeclarationDTO(
            provider_reference="provider:local-a",
            capability_states=(ProviderCapabilityStateDTO(capability_id="text_prompt", state="supported"),),
        ),
    )
    readiness = PreExecutionReadinessService().validate(
        PreExecutionReadinessInputDTO(
            request_validation_report=request_report,
            capability_negotiation_report=negotiation_report,
            provider_reference="provider:local-a",
        )
    )
    records = [
        ExecutionAuthorizationRecordDTO(
            authorization_id="authorization:001",
            authorizer_id="human:editor-a",
            authorized_at=datetime(2026, 8, 22, 12, 0, tzinfo=UTC),
            request_id=request.request_id,
            provider_reference="provider:local-a",
        )
    ]
    if multiple_authorizers:
        records.append(
            ExecutionAuthorizationRecordDTO(
                authorization_id="authorization:002",
                authorizer_id="human:editor-b",
                authorized_at=datetime(2026, 8, 22, 12, 1, tzinfo=UTC),
                request_id=request.request_id,
                provider_reference="provider:local-a",
            )
        )
    return ExecutionAuthorizationValidationService().validate(readiness, tuple(records))


def _envelope(
    authorization_ids: tuple[str, ...] = ("authorization:001",),
    **updates: object,
) -> AuthorizedGenerationExecutionEnvelopeDTO:
    values: dict[str, object] = {
        "attempt_id": "attempt:001",
        "request_id": "request:001",
        "provider_reference": "provider:local-a",
        "authorization_ids": authorization_ids,
        "profile_id": "profile:manga",
        "profile_version": "v1",
        "generation_intent_reference": "intent:001",
        "input_reference": "input:001",
    }
    values.update(updates)
    return AuthorizedGenerationExecutionEnvelopeDTO(**values)


def _validate(report, *envelopes: AuthorizedGenerationExecutionEnvelopeDTO):
    return AuthorizedGenerationExecutionEnvelopeValidationService().validate(envelopes, report)


def test_envelope_is_frozen_closed_and_uses_safe_logical_references() -> None:
    envelope = _envelope()

    with pytest.raises(ValidationError):
        envelope.attempt_id = "attempt:changed"
    with pytest.raises(ValidationError):
        AuthorizedGenerationExecutionEnvelopeDTO(**envelope.model_dump(), raw_prompt="private")
    with pytest.raises(ValidationError):
        _envelope(input_reference="https://private")
    with pytest.raises(ValidationError):
        _envelope(authorization_ids=("person@example.com",))


def test_valid_envelope_and_authorization_set_ordering_are_ready() -> None:
    authorization_report = _authorization_report(multiple_authorizers=True)

    report = _validate(
        authorization_report,
        _envelope(authorization_ids=("authorization:002", "authorization:001")),
    )

    assert report.status == "ready"
    assert report.ready is True
    assert report.envelopes[0].authorization_ids == ("authorization:001", "authorization:002")


@pytest.mark.parametrize(
    ("authorization_ids", "code"),
    (
        (("authorization:001",), "EXECUTION_ENVELOPE_AUTHORIZATION_BINDING_MISMATCH"),
        (("authorization:001", "authorization:002", "authorization:extra"), "EXECUTION_ENVELOPE_AUTHORIZATION_BINDING_MISMATCH"),
        (("authorization:001", "authorization:001", "authorization:002"), "DUPLICATE_AUTHORIZATION_BINDING"),
    ),
)
def test_authorization_set_must_be_exact_and_duplicate_free(
    authorization_ids: tuple[str, ...], code: str
) -> None:
    report = _validate(_authorization_report(multiple_authorizers=True), _envelope(authorization_ids))

    assert report.status == "blocked"
    assert code in {item.code for item in report.findings}


def test_all_snapshot_bindings_must_exactly_match() -> None:
    report = _validate(
        _authorization_report(),
        _envelope(
            request_id="request:other",
            provider_reference="provider:other",
            profile_id="profile:other",
            profile_version="v2",
            generation_intent_reference="intent:other",
            input_reference="input:other",
        ),
    )

    assert report.status == "blocked"
    assert {
        "EXECUTION_ENVELOPE_REQUEST_MISMATCH",
        "EXECUTION_ENVELOPE_PROVIDER_MISMATCH",
        "EXECUTION_ENVELOPE_PROFILE_MISMATCH",
        "EXECUTION_ENVELOPE_GENERATION_INTENT_MISMATCH",
        "EXECUTION_ENVELOPE_INPUT_REFERENCE_MISMATCH",
    } <= {item.code for item in report.findings}


def test_duplicate_attempt_ids_are_blocked() -> None:
    report = _validate(
        _authorization_report(),
        _envelope(),
        _envelope(attempt_id="attempt:001"),
    )

    assert report.status == "blocked"
    assert "DUPLICATE_EXECUTION_ATTEMPT_ID" in {item.code for item in report.findings}


def test_missing_or_non_ready_authorization_cannot_be_overridden() -> None:
    authorization_report = _authorization_report()
    needs_review = authorization_report.model_copy(update={"status": "needs_review", "ready": False})
    blocked = authorization_report.model_copy(update={"status": "blocked", "ready": False})

    missing = _validate(authorization_report)
    review = _validate(needs_review, _envelope())
    rejected = _validate(blocked, _envelope())

    assert [item.code for item in missing.findings] == ["MISSING_AUTHORIZED_EXECUTION_ENVELOPE"]
    assert review.status == "needs_review"
    assert [item.code for item in review.findings] == ["AUTHORIZATION_VALIDATION_NEEDS_REVIEW"]
    assert rejected.status == "blocked"
    assert [item.code for item in rejected.findings] == ["AUTHORIZATION_VALIDATION_BLOCKED"]


def test_input_is_non_mutating_and_reports_are_deterministic_and_canonical() -> None:
    authorization_report = _authorization_report(multiple_authorizers=True)
    envelopes = (
        _envelope(
            attempt_id="attempt:z",
            authorization_ids=("authorization:002", "authorization:001"),
        ),
        _envelope(
            attempt_id="attempt:a",
            authorization_ids=("authorization:001", "authorization:002"),
        ),
    )
    before = (
        authorization_report.model_dump(mode="json"),
        tuple(item.model_dump(mode="json") for item in envelopes),
    )

    first = _validate(authorization_report, *envelopes)
    second = _validate(authorization_report, *envelopes)

    assert (
        authorization_report.model_dump(mode="json"),
        tuple(item.model_dump(mode="json") for item in envelopes),
    ) == before
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert tuple(item.attempt_id for item in first.envelopes) == ("attempt:a", "attempt:z")


def test_source_keeps_prompt_execution_runtime_and_public_exports_out() -> None:
    source = (
        ROOT
        / "src/manga_director/production/next_generation_authorized_execution_envelope.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "manga_director.adapters",
        "manga_director.agents",
        "manga_director.plugins",
        "manga_director.workflow",
        "manga_director.domain.state_machine",
        "GenerationEvidenceEnvelopeDTO",
        ".execute(",
        ".generate(",
        ".retry(",
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
    assert "next_generation_authorized_execution_envelope" not in production_init
    assert "next_generation_authorized_execution_envelope" not in root_init
