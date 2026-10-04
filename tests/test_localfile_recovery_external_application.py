"""Focused fake-only tests for the private Recovery external-application bridge."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    DurableEvidenceWorkflowBindingReport,
    WorkflowApplicationAuthorizationDTO,
)
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
    ProviderCapabilityDeclarationDTO,
    ProviderCapabilityNegotiationService,
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
from manga_director.workflow.localfile_external_generated_application import (
    ExternalGeneratedApplicationResult,
)
from manga_director.workflow.localfile_recovery_external_application import (
    LocalFileRecoveryExternalApplicationBridge,
    RecoveryAuthoritativeWorkflowPageMappingDTO,
    RecoveryExternalApplicationInputDTO,
)

ROOT = Path(__file__).resolve().parents[1]
_SOURCE_ATTEMPT = "attempt:source:001"
_SOURCE_OUTPUT = "asset:source:001"
_ATTEMPT = "attempt:recovery:001"
_OUTPUT = "asset:recovery:001"
_PROVIDER = "provider:local-a"
_PROJECT = "project:recovery:001"
_PAGE = "page:v6:001"
_TARGET = "target:v6:001"


class _Coordinator:
    def __init__(self, result: ExternalGeneratedApplicationResult | None = None) -> None:
        self.calls: list[tuple[object, object]] = []
        self.result = result or ExternalGeneratedApplicationResult(
            project_id=_PROJECT,
            page_id=_PAGE,
            status="application_applied_event_published",
            code="EXTERNAL_APPLICATION_APPLIED",
            event_published=True,
        )

    def apply(self, binding_report: object, authorization: object) -> ExternalGeneratedApplicationResult:
        self.calls.append((binding_report, authorization))
        return self.result


def _known(value: str) -> EvidenceValueDTO:
    return EvidenceValueDTO(availability="known", value=value)


def _recovery_authorization_report():
    proposal = GenerationRecoveryProposalDTO(
        proposal_id="proposal:recovery:001",
        source_decision_id="decision:recovery:001",
        source_attempt_id=_SOURCE_ATTEMPT,
        source_output_asset_id=_SOURCE_OUTPUT,
        source_provenance_reference="provenance:source:001",
        target_page_id="recovery-page:001",
        target_panel_id="recovery-panel:001",
        requested_change_scopes=("prompt",),
        preservation_scopes=("identity_bindings",),
        authorization_required=True,
    )
    decision = HumanReviewDecisionRecordDTO(
        decision_id="decision:recovery:001",
        reviewer_id="reviewer:recovery:001",
        reviewed_at=datetime(2026, 8, 23, tzinfo=UTC),
        qa_report_reference="qa:recovery:001",
        target_type="finding",
        target_reference="finding:recovery:001",
        decision="change_requested",
    )
    evidence = GenerationEvidenceEnvelopeDTO(
        attempt_id=_SOURCE_ATTEMPT,
        observed_at=datetime(2026, 8, 23, tzinfo=UTC),
        provenance_reference="provenance:source:001",
        input=GenerationInputEvidenceDTO(input_reference="input:source:001"),
        output=GenerationOutputEvidenceDTO(output_asset_id=_SOURCE_OUTPUT),
        configuration=GenerationConfigurationEvidenceDTO(
            provider_id=_known(_PROVIDER),
            model_id=_known("model:fake"),
            model_version=_known("v1"),
            workflow_id=_known("workflow:fake"),
            workflow_version=_known("v1"),
            seed=_known("1"),
        ),
    )
    proposal_report = GenerationRecoveryProposalValidationService().validate(
        (proposal,),
        human_review_decision_validation_report=HumanReviewDecisionValidationService().validate((decision,)),
        generation_evidence_validation_report=GenerationEvidenceValidationService().validate((evidence,)),
    )
    request = RecoveryStructuredGenerationRequestDTO(
        recovery_request_id="request:recovery:001",
        recovery_proposal_id=proposal.proposal_id,
        generation_intent_reference="intent:recovery:001",
        input=GenerationInputEvidenceDTO(input_reference="input:recovery:001"),
        profile_id="profile:recovery:001",
        profile_version="v1",
        capability_requirements=(),
        identity_bindings=(
            GenerationIdentityBindingDTO(
                character_id="character:recovery:001",
                identity_id="identity:recovery:001",
                identity_version="v1",
                reference_asset_ids=("asset:identity:001",),
            ),
        ),
    )
    request_report = RecoveryStructuredGenerationRequestValidationService().validate(
        request,
        GenerationProductionProfileDTO(
            profile_id=request.profile_id,
            profile_version=request.profile_version,
            capability_requirements=(),
        ),
    )
    negotiation = ProviderCapabilityNegotiationService().validate(
        (), ProviderCapabilityDeclarationDTO(provider_reference=_PROVIDER, capability_states=())
    )
    readiness = RecoveryPreExecutionReadinessService().validate(
        RecoveryPreExecutionReadinessInputDTO(
            recovery_proposal_validation_report=proposal_report,
            recovery_request_validation_report=request_report,
            capability_negotiation_report=negotiation,
            provider_reference=_PROVIDER,
        )
    )
    return RecoveryExecutionAuthorizationValidationService().validate(
        readiness,
        (
            RecoveryExecutionAuthorizationRecordDTO(
                authorization_id="authorization:recovery:001",
                authorizer_id="human:recovery:001",
                authorized_at=datetime(2026, 8, 23, tzinfo=UTC),
                recovery_proposal_id=proposal.proposal_id,
                recovery_request_id=request.recovery_request_id,
                provider_reference=_PROVIDER,
            ),
        ),
    )


def _mapping(**updates: object) -> RecoveryAuthoritativeWorkflowPageMappingDTO:
    values: dict[str, object] = {
        "recovery_proposal_id": "proposal:recovery:001",
        "recovery_request_id": "request:recovery:001",
        "recovery_target_page_id": "recovery-page:001",
        "recovery_target_panel_id": "recovery-panel:001",
        "project_id": _PROJECT,
        "page_id": _PAGE,
        "target_page_reference": _TARGET,
    }
    values.update(updates)
    return RecoveryAuthoritativeWorkflowPageMappingDTO.model_validate(values)


def _binding(**updates: object) -> DurableEvidenceWorkflowBindingReport:
    values: dict[str, object] = {
        "attempt_id": _ATTEMPT,
        "provider_reference": _PROVIDER,
        "output_asset_id": _OUTPUT,
        "project_id": _PROJECT,
        "page_id": _PAGE,
        "target_page_reference": _TARGET,
        "status": "eligible",
        "eligible": True,
    }
    values.update(updates)
    return DurableEvidenceWorkflowBindingReport.model_validate(values)


def _authorization(**updates: object) -> WorkflowApplicationAuthorizationDTO:
    values: dict[str, object] = {
        "authorization_id": "authorization:normal:001",
        "authorizer_id": "human:normal:001",
        "authorized_at": datetime(2026, 8, 23, tzinfo=UTC),
        "attempt_id": _ATTEMPT,
        "provider_reference": _PROVIDER,
        "project_id": _PROJECT,
        "page_id": _PAGE,
        "target_page_reference": _TARGET,
        "source_state": "PromptBuilt",
        "target_state": "Generated",
    }
    values.update(updates)
    return WorkflowApplicationAuthorizationDTO.model_validate(values)


def _input(**updates: object) -> RecoveryExternalApplicationInputDTO:
    values: dict[str, object] = {
        "recovery_authorization_report": _recovery_authorization_report(),
        "authoritative_mapping": _mapping(),
        "normal_binding_report": _binding(),
        "normal_authorization": _authorization(),
    }
    values.update(updates)
    return RecoveryExternalApplicationInputDTO.model_validate(values)


def test_valid_recovery_input_delegates_exact_existing_normal_contract() -> None:
    coordinator = _Coordinator()
    input = _input()

    result = LocalFileRecoveryExternalApplicationBridge(coordinator).apply(input)  # type: ignore[arg-type]

    assert result.report.status == "delegated"
    assert result.application_result is coordinator.result
    assert coordinator.calls == [(input.normal_binding_report, input.normal_authorization)]


@pytest.mark.parametrize(
    ("updates", "code"),
    (
        ({"normal_binding_report": _binding(attempt_id=_SOURCE_ATTEMPT)}, "RECOVERY_ATTEMPT_ID_NOT_DISTINCT"),
        ({"normal_binding_report": _binding(output_asset_id=_SOURCE_OUTPUT)}, "RECOVERY_OUTPUT_ASSET_ID_NOT_DISTINCT"),
        ({"authoritative_mapping": _mapping(page_id="page:v6:other")}, "NORMAL_BINDING_TARGET_MISMATCH"),
        ({"normal_authorization": _authorization(provider_reference="provider:other")}, "NORMAL_AUTHORIZATION_BINDING_MISMATCH"),
        ({"normal_binding_report": _binding(provider_reference="provider:other")}, "RECOVERY_PROVIDER_BINDING_MISMATCH"),
    ),
)
def test_identity_mapping_authorization_and_provider_conflicts_fail_before_delegation(
    updates: dict[str, object], code: str
) -> None:
    coordinator = _Coordinator()

    result = LocalFileRecoveryExternalApplicationBridge(coordinator).apply(_input(**updates))  # type: ignore[arg-type]

    assert result.report.status == "blocked"
    assert code in {item.code for item in result.report.findings}
    assert result.application_result is None
    assert coordinator.calls == []


def test_unready_recovery_evidence_and_noneligible_normal_binding_fail_closed() -> None:
    coordinator = _Coordinator()
    unready = _recovery_authorization_report().model_copy(update={"status": "needs_review", "ready": False})
    first = LocalFileRecoveryExternalApplicationBridge(coordinator).apply(
        _input(recovery_authorization_report=unready)
    )  # type: ignore[arg-type]
    second = LocalFileRecoveryExternalApplicationBridge(coordinator).apply(
        _input(normal_binding_report=_binding(status="blocked", eligible=False))
    )  # type: ignore[arg-type]

    assert "RECOVERY_AUTHORIZATION_NOT_READY" in {item.code for item in first.report.findings}
    assert "NORMAL_BINDING_NOT_ELIGIBLE" in {item.code for item in second.report.findings}
    assert coordinator.calls == []


@pytest.mark.parametrize(
    "status",
    (
        "application_applied_event_published",
        "application_not_applied",
        "application_replay_confirmed",
        "application_applied_ledger_finalize_failed",
        "application_applied_event_failed",
    ),
)
def test_recovery_matrix_outcomes_are_delegated_without_bridge_repair_or_retry(status: str) -> None:
    coordinator = _Coordinator(
        ExternalGeneratedApplicationResult(
            project_id=_PROJECT,
            page_id=_PAGE,
            status=status,  # type: ignore[arg-type]
            code="SYNTHETIC_COORDINATOR_OUTCOME",
            event_published=False,
        )
    )

    result = LocalFileRecoveryExternalApplicationBridge(coordinator).apply(_input())  # type: ignore[arg-type]

    assert result.application_result is coordinator.result
    assert len(coordinator.calls) == 1


def test_private_dtos_are_frozen_closed_deterministic_and_non_mutating() -> None:
    input = _input()
    before = input.model_dump(mode="json")
    bridge = LocalFileRecoveryExternalApplicationBridge(_Coordinator())  # type: ignore[arg-type]
    first = bridge.validate(input)
    second = bridge.validate(input)

    with pytest.raises(ValidationError):
        RecoveryAuthoritativeWorkflowPageMappingDTO(**_mapping().model_dump(), raw_path="private")
    with pytest.raises(ValidationError):
        _mapping().page_id = "changed"
    assert input.model_dump(mode="json") == before
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_source_does_not_use_workflow_recovery_or_expose_private_bridge() -> None:
    source = (
        ROOT / "src/manga_director/workflow/localfile_recovery_external_application.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "WorkflowRecovery",
        ".resume_step(",
        "manga_director.adapters",
        "manga_director.agents",
        ".generate(",
        ".execute(",
        "open(",
        "read_text(",
        "requests.",
        "httpx.",
        "datetime.now",
    ):
        assert forbidden not in source
    assert "localfile_recovery_external_application" not in (
        ROOT / "src/manga_director/workflow/__init__.py"
    ).read_text(encoding="utf-8")
    assert "localfile_recovery_external_application" not in (
        ROOT / "src/manga_director/__init__.py"
    ).read_text(encoding="utf-8")
