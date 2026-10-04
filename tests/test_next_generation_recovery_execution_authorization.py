"""Focused contracts for internal Recovery Execution Authorization validation."""

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
)
from manga_director.production.next_generation_generation_recovery_proposal import (
    GenerationRecoveryProposalDTO,
    GenerationRecoveryProposalValidationService,
)
from manga_director.production.next_generation_human_review_decision import (
    HumanReviewDecisionRecordDTO,
    HumanReviewDecisionValidationService,
)
from manga_director.production.next_generation_provider_capability_negotiation import (
    GenerationCapabilityRequirementDTO,
    ProviderCapabilityDeclarationDTO,
    ProviderCapabilityNegotiationService,
    ProviderCapabilityStateDTO,
)
from manga_director.production.next_generation_recovery_execution_authorization import (
    RecoveryExecutionAuthorizationRecordDTO,
    RecoveryExecutionAuthorizationValidationService,
)
from manga_director.production.next_generation_recovery_pre_execution_readiness import (
    RecoveryPreExecutionReadinessInputDTO,
    RecoveryPreExecutionReadinessService,
)
from manga_director.production.next_generation_recovery_structured_generation_request import (
    RecoveryStructuredGenerationRequestDTO,
    RecoveryStructuredGenerationRequestValidationService,
)
from manga_director.production.next_generation_structured_generation_request import (
    GenerationProductionProfileDTO,
)

ROOT = Path(__file__).resolve().parents[1]


def _known(value: str) -> EvidenceValueDTO:
    return EvidenceValueDTO(availability="known", value=value)


def _requirement(capability_id: str, level: str = "required") -> GenerationCapabilityRequirementDTO:
    return GenerationCapabilityRequirementDTO(
        capability_id=capability_id,
        requirement_level=level,
    )


def _proposal_report():
    proposal = GenerationRecoveryProposalDTO(
        proposal_id="proposal:001",
        source_decision_id="decision:001",
        source_attempt_id="attempt:001",
        source_output_asset_id="asset:001",
        source_provenance_reference="provenance:001",
        target_page_id="page:001",
        target_panel_id="panel:001",
        requested_change_scopes=("prompt",),
        preservation_scopes=("identity_bindings",),
        authorization_required=True,
    )
    decision = HumanReviewDecisionRecordDTO(
        decision_id="decision:001",
        reviewer_id="reviewer:one",
        reviewed_at=datetime(2026, 8, 22, tzinfo=UTC),
        qa_report_reference="qa:001",
        target_type="finding",
        target_reference="finding:001",
        decision="change_requested",
    )
    decision_report = HumanReviewDecisionValidationService().validate((decision,))
    envelope = GenerationEvidenceEnvelopeDTO(
        attempt_id="attempt:001",
        observed_at=datetime(2026, 8, 22, tzinfo=UTC),
        provenance_reference="provenance:001",
        input=GenerationInputEvidenceDTO(input_reference="input:001"),
        output=GenerationOutputEvidenceDTO(output_asset_id="asset:001"),
        configuration=GenerationConfigurationEvidenceDTO(
            provider_id=_known("provider:local-a"),
            model_id=_known("model:mock"),
            model_version=_known("v1"),
            workflow_id=_known("workflow:page"),
            workflow_version=_known("v1"),
            seed=_known("1"),
        ),
    )
    evidence_report = GenerationEvidenceValidationService().validate((envelope,))
    return GenerationRecoveryProposalValidationService().validate(
        (proposal,),
        human_review_decision_validation_report=decision_report,
        generation_evidence_validation_report=evidence_report,
    )


def _recovery_readiness(
    *requirements: GenerationCapabilityRequirementDTO,
    states: tuple[ProviderCapabilityStateDTO, ...] = (),
):
    profile = GenerationProductionProfileDTO(
        profile_id="profile:recovery",
        profile_version="v1",
        capability_requirements=requirements,
    )
    request = RecoveryStructuredGenerationRequestDTO(
        recovery_request_id="recovery-request:001",
        recovery_proposal_id="proposal:001",
        generation_intent_reference="recovery-intent:001",
        input=GenerationInputEvidenceDTO(input_reference="recovery-input:001"),
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        capability_requirements=requirements,
        identity_bindings=(
            GenerationIdentityBindingDTO(
                character_id="character:aki",
                identity_id="identity:aki:v1",
                identity_version="v1",
                reference_asset_ids=("asset:aki:front",),
            ),
        ),
    )
    request_report = RecoveryStructuredGenerationRequestValidationService().validate(request, profile)
    negotiation_report = ProviderCapabilityNegotiationService().validate(
        requirements,
        ProviderCapabilityDeclarationDTO(
            provider_reference="provider:local-a",
            capability_states=states,
        ),
    )
    return RecoveryPreExecutionReadinessService().validate(
        RecoveryPreExecutionReadinessInputDTO(
            recovery_proposal_validation_report=_proposal_report(),
            recovery_request_validation_report=request_report,
            capability_negotiation_report=negotiation_report,
            provider_reference="provider:local-a",
        )
    )


def _record(
    authorization_id: str = "recovery-authorization:001",
    authorizer_id: str = "human:editor-a",
    recovery_proposal_id: str = "proposal:001",
    recovery_request_id: str = "recovery-request:001",
    provider_reference: str = "provider:local-a",
    rationale_reference: str | None = None,
) -> RecoveryExecutionAuthorizationRecordDTO:
    return RecoveryExecutionAuthorizationRecordDTO(
        authorization_id=authorization_id,
        authorizer_id=authorizer_id,
        authorized_at=datetime(2026, 8, 22, 12, 0, tzinfo=UTC),
        recovery_proposal_id=recovery_proposal_id,
        recovery_request_id=recovery_request_id,
        provider_reference=provider_reference,
        rationale_reference=rationale_reference,
    )


def _validate(readiness, *records: RecoveryExecutionAuthorizationRecordDTO):
    return RecoveryExecutionAuthorizationValidationService().validate(readiness, records)


def test_record_is_frozen_closed_timezone_aware_and_reference_safe() -> None:
    record = _record()

    with pytest.raises(ValidationError):
        record.authorizer_id = "human:editor-b"
    with pytest.raises(ValidationError):
        RecoveryExecutionAuthorizationRecordDTO(**record.model_dump(), raw_rationale="private")
    with pytest.raises(ValidationError):
        _record(rationale_reference="https://private")
    with pytest.raises(ValidationError):
        _record(authorizer_id="person@example.com")
    with pytest.raises(ValidationError):
        RecoveryExecutionAuthorizationRecordDTO(
            **record.model_dump(exclude={"authorized_at"}),
            authorized_at=datetime(2026, 8, 22, 12, 0),
        )


def test_valid_single_and_multiple_distinct_authorizers_are_ready() -> None:
    readiness = _recovery_readiness()

    single = _validate(readiness, _record(rationale_reference="rationale:001"))
    multiple = _validate(
        readiness,
        _record(authorization_id="recovery-authorization:002", authorizer_id="human:editor-b"),
        _record(),
    )

    assert single.status == "ready"
    assert single.ready is True
    assert tuple(item.authorizer_id for item in multiple.authorization_records) == (
        "human:editor-a",
        "human:editor-b",
    )
    assert multiple.status == "ready"


def test_missing_authorization_needs_review() -> None:
    report = _validate(_recovery_readiness())

    assert report.status == "needs_review"
    assert [item.code for item in report.findings] == ["MISSING_RECOVERY_EXECUTION_AUTHORIZATION"]


def test_recovery_readiness_needs_review_and_blocked_cannot_be_overridden() -> None:
    ready = _recovery_readiness()
    needs_review = ready.model_copy(update={"status": "needs_review", "ready": False})
    blocked = ready.model_copy(update={"status": "blocked", "ready": False})

    review_report = _validate(needs_review, _record())
    blocked_report = _validate(blocked, _record())

    assert review_report.status == "needs_review"
    assert [item.code for item in review_report.findings] == ["RECOVERY_READINESS_NEEDS_REVIEW"]
    assert blocked_report.status == "blocked"
    assert [item.code for item in blocked_report.findings] == ["RECOVERY_READINESS_BLOCKED"]


def test_duplicate_authorization_id_and_same_authorizer_target_are_blocked() -> None:
    readiness = _recovery_readiness()
    duplicate_id = _validate(
        readiness,
        _record(),
        _record(authorization_id="recovery-authorization:001", authorizer_id="human:editor-b"),
    )
    duplicate_target = _validate(
        readiness,
        _record(),
        _record(authorization_id="recovery-authorization:002"),
    )

    assert "DUPLICATE_RECOVERY_AUTHORIZATION_ID" in {item.code for item in duplicate_id.findings}
    assert "DUPLICATE_RECOVERY_AUTHORIZER_TARGET" in {
        item.code for item in duplicate_target.findings
    }


def test_proposal_request_and_provider_mismatches_are_blocked() -> None:
    report = _validate(
        _recovery_readiness(),
        _record(
            recovery_proposal_id="proposal:other",
            recovery_request_id="recovery-request:other",
            provider_reference="provider:other",
        ),
    )

    assert report.status == "blocked"
    assert {
        "RECOVERY_AUTHORIZATION_PROPOSAL_MISMATCH",
        "RECOVERY_AUTHORIZATION_REQUEST_MISMATCH",
        "RECOVERY_AUTHORIZATION_PROVIDER_MISMATCH",
    } <= {item.code for item in report.findings}


def test_input_is_non_mutating_and_results_are_deterministic_and_canonical() -> None:
    readiness = _recovery_readiness()
    records = (
        _record(authorization_id="recovery-authorization:002", authorizer_id="human:editor-b"),
        _record(),
    )
    before = (readiness.model_dump(mode="json"), tuple(item.model_dump(mode="json") for item in records))

    first = _validate(readiness, *records)
    second = _validate(readiness, *records)

    assert (readiness.model_dump(mode="json"), tuple(item.model_dump(mode="json") for item in records)) == before
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert tuple(item.authorizer_id for item in first.authorization_records) == (
        "human:editor-a",
        "human:editor-b",
    )


def test_source_keeps_normal_authorization_execution_and_public_exports_out() -> None:
    source = (
        ROOT
        / "src/manga_director/production/next_generation_recovery_execution_authorization.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "from manga_director.production.next_generation_execution_authorization import",
        "manga_director.security",
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
        "datetime.now",
    ):
        assert forbidden not in source
    production_init = (ROOT / "src/manga_director/production/__init__.py").read_text(
        encoding="utf-8"
    )
    root_init = (ROOT / "src/manga_director/__init__.py").read_text(encoding="utf-8")
    assert "next_generation_recovery_execution_authorization" not in production_init
    assert "next_generation_recovery_execution_authorization" not in root_init
