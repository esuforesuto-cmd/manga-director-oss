"""Focused contracts for internal Recovery Pre-Execution Readiness validation."""

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
    GenerationRecoveryProposalFindingDTO,
    GenerationRecoveryProposalValidationReport,
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


def _requirement(capability_id: str, level: str = "required") -> GenerationCapabilityRequirementDTO:
    return GenerationCapabilityRequirementDTO(
        capability_id=capability_id,
        requirement_level=level,
    )


def _state(capability_id: str, state: str) -> ProviderCapabilityStateDTO:
    return ProviderCapabilityStateDTO(capability_id=capability_id, state=state)


def _known(value: str) -> EvidenceValueDTO:
    return EvidenceValueDTO(availability="known", value=value)


def _proposal(**updates: object) -> GenerationRecoveryProposalDTO:
    values: dict[str, object] = {
        "proposal_id": "proposal:001",
        "source_decision_id": "decision:001",
        "source_attempt_id": "attempt:001",
        "source_output_asset_id": "asset:001",
        "source_provenance_reference": "provenance:001",
        "target_page_id": "page:001",
        "target_panel_id": "panel:001",
        "requested_change_scopes": ("prompt",),
        "preservation_scopes": ("identity_bindings",),
        "authorization_required": True,
    }
    values.update(updates)
    return GenerationRecoveryProposalDTO(**values)


def _proposal_report(proposal: GenerationRecoveryProposalDTO | None = None):
    decision = HumanReviewDecisionRecordDTO(
        decision_id="decision:001",
        reviewer_id="reviewer:one",
        reviewed_at=datetime(2026, 8, 21, tzinfo=UTC),
        qa_report_reference="qa:001",
        target_type="finding",
        target_reference="finding:001",
        decision="change_requested",
    )
    decision_report = HumanReviewDecisionValidationService().validate((decision,))
    configuration = GenerationConfigurationEvidenceDTO(
        provider_id=_known("provider:local-a"),
        model_id=_known("model:mock"),
        model_version=_known("v1"),
        workflow_id=_known("workflow:page"),
        workflow_version=_known("v1"),
        seed=_known("1"),
    )
    envelope = GenerationEvidenceEnvelopeDTO(
        attempt_id="attempt:001",
        observed_at=datetime(2026, 8, 21, tzinfo=UTC),
        provenance_reference="provenance:001",
        input=GenerationInputEvidenceDTO(input_reference="input:001"),
        output=GenerationOutputEvidenceDTO(output_asset_id="asset:001"),
        configuration=configuration,
    )
    evidence_report = GenerationEvidenceValidationService().validate((envelope,))
    return GenerationRecoveryProposalValidationService().validate(
        (_proposal() if proposal is None else proposal,),
        human_review_decision_validation_report=decision_report,
        generation_evidence_validation_report=evidence_report,
    )


def _request_report(
    *requirements: GenerationCapabilityRequirementDTO,
    proposal_id: str = "proposal:001",
    request_requirements: tuple[GenerationCapabilityRequirementDTO, ...] | None = None,
    profile_requirements: tuple[GenerationCapabilityRequirementDTO, ...] | None = None,
):
    profile_values = requirements if profile_requirements is None else profile_requirements
    request_values = requirements if request_requirements is None else request_requirements
    profile = GenerationProductionProfileDTO(
        profile_id="profile:recovery",
        profile_version="v1",
        capability_requirements=profile_values,
    )
    request = RecoveryStructuredGenerationRequestDTO(
        recovery_request_id="recovery-request:001",
        recovery_proposal_id=proposal_id,
        generation_intent_reference="recovery-intent:001",
        input=GenerationInputEvidenceDTO(input_reference="recovery-input:001"),
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        capability_requirements=request_values,
        identity_bindings=(
            GenerationIdentityBindingDTO(
                character_id="character:aki",
                identity_id="identity:aki:v1",
                identity_version="v1",
                reference_asset_ids=("asset:aki:front",),
            ),
        ),
    )
    return RecoveryStructuredGenerationRequestValidationService().validate(request, profile)


def _negotiation_report(
    requirements: tuple[GenerationCapabilityRequirementDTO, ...],
    *states: ProviderCapabilityStateDTO,
    provider_reference: str = "provider:local-a",
):
    return ProviderCapabilityNegotiationService().validate(
        requirements,
        ProviderCapabilityDeclarationDTO(
            provider_reference=provider_reference,
            capability_states=states,
        ),
    )


def _validate(
    proposal_report,
    request_report,
    negotiation_report,
    provider_reference: str = "provider:local-a",
):
    return RecoveryPreExecutionReadinessService().validate(
        RecoveryPreExecutionReadinessInputDTO(
            recovery_proposal_validation_report=proposal_report,
            recovery_request_validation_report=request_report,
            capability_negotiation_report=negotiation_report,
            provider_reference=provider_reference,
        )
    )


def test_dtos_are_frozen_closed_and_validate_logical_provider_reference() -> None:
    proposal_report = _proposal_report()
    request_report = _request_report(_requirement("text_prompt"))
    negotiation_report = _negotiation_report(
        (_requirement("text_prompt"),), _state("text_prompt", "supported")
    )
    readiness_input = RecoveryPreExecutionReadinessInputDTO(
        recovery_proposal_validation_report=proposal_report,
        recovery_request_validation_report=request_report,
        capability_negotiation_report=negotiation_report,
        provider_reference="provider:local-a",
    )

    with pytest.raises(ValidationError):
        readiness_input.provider_reference = "provider:changed"
    with pytest.raises(ValidationError):
        RecoveryPreExecutionReadinessInputDTO(
            **readiness_input.model_dump(exclude={"provider_reference"}),
            provider_reference="https://provider",
        )
    with pytest.raises(ValidationError):
        RecoveryPreExecutionReadinessInputDTO(**readiness_input.model_dump(), raw_prompt="private")


def test_authorization_required_only_proposal_is_eligible_and_not_authorization() -> None:
    proposal_report = _proposal_report()
    request_report = _request_report(_requirement("text_prompt"))
    negotiation_report = _negotiation_report(
        (_requirement("text_prompt"),), _state("text_prompt", "supported")
    )

    report = _validate(proposal_report, request_report, negotiation_report)

    assert [(item.code, item.status) for item in proposal_report.findings] == [
        ("AUTHORIZATION_REQUIRED", "needs_review")
    ]
    assert report.status == "ready"
    assert report.ready is True


def test_blocked_proposal_report_is_fail_closed() -> None:
    proposal_report = _proposal_report(_proposal(authorization_required=False))
    request_report = _request_report()
    negotiation_report = _negotiation_report(())

    report = _validate(proposal_report, request_report, negotiation_report)

    assert report.status == "blocked"
    assert "RECOVERY_PROPOSAL_VALIDATION_BLOCKED" in {item.code for item in report.findings}


def test_unknown_proposal_needs_review_reason_remains_needs_review() -> None:
    proposal = _proposal()
    proposal_report = GenerationRecoveryProposalValidationReport(
        proposals=(proposal,),
        findings=(
            GenerationRecoveryProposalFindingDTO(
                code="FUTURE_REVIEW_REASON",
                status="needs_review",
                message="future review reason",
                proposal_id=proposal.proposal_id,
            ),
        ),
        status="needs_review",
        ready=False,
    )
    request_report = _request_report()
    negotiation_report = _negotiation_report(())

    report = _validate(proposal_report, request_report, negotiation_report)

    assert [(item.code, item.status) for item in report.findings] == [
        ("RECOVERY_PROPOSAL_NEEDS_REVIEW", "needs_review")
    ]


def test_request_proposal_provider_and_requirement_integrity_fail_closed() -> None:
    proposal_report = _proposal_report()
    blocked_request = _request_report(
        _requirement("text_prompt"),
        request_requirements=(_requirement("seed"),),
    )
    mismatch_request = _request_report(proposal_id="proposal:other")
    requirements_request = _request_report(_requirement("text_prompt"))
    blocked_negotiation = _negotiation_report(
        (_requirement("text_prompt"), _requirement("text_prompt")),
        _state("text_prompt", "supported"),
        _state("text_prompt", "supported"),
    )

    blocked = _validate(proposal_report, blocked_request, _negotiation_report((_requirement("seed"),)))
    proposal_mismatch = _validate(proposal_report, mismatch_request, _negotiation_report(()))
    provider_mismatch = _validate(
        proposal_report,
        requirements_request,
        _negotiation_report((_requirement("text_prompt"),), _state("text_prompt", "supported"), provider_reference="provider:local-b"),
    )
    requirement_mismatch = _validate(proposal_report, requirements_request, _negotiation_report(()))
    negotiation_blocked = _validate(proposal_report, requirements_request, blocked_negotiation)

    assert "RECOVERY_REQUEST_VALIDATION_BLOCKED" in {item.code for item in blocked.findings}
    assert "RECOVERY_PROPOSAL_REQUEST_MISMATCH" in {item.code for item in proposal_mismatch.findings}
    assert "RECOVERY_PROVIDER_REFERENCE_MISMATCH" in {item.code for item in provider_mismatch.findings}
    assert "RECOVERY_REQUEST_NEGOTIATION_REQUIREMENT_MISMATCH" in {
        item.code for item in requirement_mismatch.findings
    }
    assert "RECOVERY_CAPABILITY_NEGOTIATION_BLOCKED" in {
        item.code for item in negotiation_blocked.findings
    }


@pytest.mark.parametrize(
    ("state", "code"),
    (
        (None, "REQUIRED_CAPABILITY_MISSING"),
        ("unsupported", "REQUIRED_CAPABILITY_UNSUPPORTED"),
        ("unknown", "REQUIRED_CAPABILITY_UNKNOWN"),
    ),
)
def test_required_capability_gaps_need_review(state: str | None, code: str) -> None:
    requirements = (_requirement("seed"),)
    states = () if state is None else (_state("seed", state),)

    report = _validate(_proposal_report(), _request_report(*requirements), _negotiation_report(requirements, *states))

    assert report.status == "needs_review"
    assert report.ready is False
    assert [(item.code, item.status) for item in report.findings] == [(code, "needs_review")]


@pytest.mark.parametrize(
    ("state", "code"),
    (
        (None, "OPTIONAL_CAPABILITY_MISSING"),
        ("unsupported", "OPTIONAL_CAPABILITY_UNSUPPORTED"),
        ("unknown", "OPTIONAL_CAPABILITY_UNKNOWN"),
    ),
)
def test_optional_capability_gaps_warn_but_keep_ready(state: str | None, code: str) -> None:
    requirements = (_requirement("seed", "optional"),)
    states = () if state is None else (_state("seed", state),)

    report = _validate(_proposal_report(), _request_report(*requirements), _negotiation_report(requirements, *states))

    assert report.status == "ready"
    assert report.ready is True
    assert [(item.code, item.status) for item in report.findings] == [(code, "warning")]


def test_identity_and_preservation_scopes_do_not_create_capability_requirements() -> None:
    report = _validate(_proposal_report(), _request_report(), _negotiation_report(()))

    assert report.status == "ready"
    assert report.findings == ()


def test_input_is_non_mutating_and_results_are_deterministic_and_canonical() -> None:
    requirements = (_requirement("text_prompt"), _requirement("seed", "optional"))
    proposal_report = _proposal_report()
    request_report = _request_report(*requirements)
    negotiation_report = _negotiation_report(
        (_requirement("seed", "optional"), _requirement("text_prompt")),
        _state("seed", "unknown"),
        _state("text_prompt", "supported"),
    )
    readiness_input = RecoveryPreExecutionReadinessInputDTO(
        recovery_proposal_validation_report=proposal_report,
        recovery_request_validation_report=request_report,
        capability_negotiation_report=negotiation_report,
        provider_reference="provider:local-a",
    )
    before = readiness_input.model_dump(mode="json")

    first = RecoveryPreExecutionReadinessService().validate(readiness_input)
    second = RecoveryPreExecutionReadinessService().validate(readiness_input)

    assert readiness_input.model_dump(mode="json") == before
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert [(item.code, item.status) for item in first.findings] == [
        ("OPTIONAL_CAPABILITY_UNKNOWN", "warning")
    ]


def test_source_keeps_normal_readiness_authorization_execution_and_exports_out() -> None:
    source = (
        ROOT
        / "src/manga_director/production/next_generation_recovery_pre_execution_readiness.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "from manga_director.production.next_generation_pre_execution_readiness import",
        "RecoveryExecutionAuthorizationRecordDTO",
        "manga_director.adapters",
        "manga_director.agents",
        "manga_director.plugins",
        "manga_director.workflow",
        "manga_director.domain.state_machine",
        "ProviderCapabilityNegotiationService",
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
    assert "next_generation_recovery_pre_execution_readiness" not in production_init
    assert "next_generation_recovery_pre_execution_readiness" not in root_init
