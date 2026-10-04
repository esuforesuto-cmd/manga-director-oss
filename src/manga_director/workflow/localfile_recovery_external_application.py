"""Private Recovery-to-normal bridge for externally generated page results.

This module owns only exact Recovery input correlation.  It deliberately
delegates all durable application behavior to the normal LocalFile external
application coordinator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import ConfigDict, field_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    DurableEvidenceWorkflowBindingReport,
    WorkflowApplicationAuthorizationDTO,
)
from manga_director.production.next_generation_generation_recovery_proposal import (
    GenerationRecoveryProposalDTO,
)
from manga_director.production.next_generation_recovery_execution_authorization import (
    RecoveryExecutionAuthorizationValidationReport,
)
from manga_director.production.next_generation_recovery_structured_generation_request import (
    RecoveryStructuredGenerationRequestDTO,
)
from manga_director.workflow.localfile_external_generated_application import (
    ExternalGeneratedApplicationResult,
    LocalFileExternalGeneratedApplicationCoordinator,
)

BridgeStatus = Literal["delegated", "blocked"]


class _RecoveryExternalApplicationModel(DirectorModel):
    """Private base for closed, immutable bridge values."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class RecoveryAuthoritativeWorkflowPageMappingDTO(_RecoveryExternalApplicationModel):
    """Trusted exact mapping from a Recovery target to one V6 workflow page."""

    recovery_proposal_id: str
    recovery_request_id: str
    recovery_target_page_id: str
    recovery_target_panel_id: str
    project_id: str
    page_id: str
    target_page_reference: str

    @field_validator(
        "recovery_proposal_id",
        "recovery_request_id",
        "recovery_target_page_id",
        "recovery_target_panel_id",
        "project_id",
        "page_id",
        "target_page_reference",
    )
    @classmethod
    def _validate_logical_reference(cls, value: str) -> str:
        return _logical_reference(value)


class RecoveryExternalApplicationInputDTO(_RecoveryExternalApplicationModel):
    """Complete caller-supplied private bridge input for one Recovery result."""

    recovery_authorization_report: RecoveryExecutionAuthorizationValidationReport
    authoritative_mapping: RecoveryAuthoritativeWorkflowPageMappingDTO
    normal_binding_report: DurableEvidenceWorkflowBindingReport
    normal_authorization: WorkflowApplicationAuthorizationDTO


class RecoveryExternalApplicationFindingDTO(_RecoveryExternalApplicationModel):
    """One deterministic redacted Recovery bridge finding."""

    code: str
    status: Literal["blocked"]
    message: str
    attempt_id: str = ""
    output_asset_id: str = ""
    project_id: str = ""
    page_id: str = ""
    target_page_reference: str = ""
    provider_reference: str = ""


class RecoveryExternalApplicationBridgeReport(_RecoveryExternalApplicationModel):
    """Read-only eligibility report before normal coordinator delegation."""

    attempt_id: str = ""
    output_asset_id: str = ""
    project_id: str = ""
    page_id: str = ""
    target_page_reference: str = ""
    provider_reference: str = ""
    findings: tuple[RecoveryExternalApplicationFindingDTO, ...] = ()
    status: BridgeStatus
    delegatable: bool
    analysis_only: Literal[True] = True


@dataclass(frozen=True, slots=True)
class RecoveryExternalApplicationResult:
    """Private bridge outcome; durable behavior remains owned by the coordinator."""

    report: RecoveryExternalApplicationBridgeReport
    application_result: ExternalGeneratedApplicationResult | None = field(default=None, repr=False)


class LocalFileRecoveryExternalApplicationBridge:
    """Validate exact Recovery correlation, then delegate once to the normal coordinator."""

    def __init__(self, coordinator: LocalFileExternalGeneratedApplicationCoordinator) -> None:
        self._coordinator = coordinator

    def apply(self, input: RecoveryExternalApplicationInputDTO) -> RecoveryExternalApplicationResult:
        """Delegate only a fully correlated Recovery application candidate."""

        report = self.validate(input)
        if report.delegatable is not True:
            return RecoveryExternalApplicationResult(report)
        return RecoveryExternalApplicationResult(
            report,
            self._coordinator.apply(input.normal_binding_report, input.normal_authorization),
        )

    def validate(
        self, input: RecoveryExternalApplicationInputDTO
    ) -> RecoveryExternalApplicationBridgeReport:
        """Validate only immutable supplied identities; never mutate or persist them."""

        binding = input.normal_binding_report
        authorization = input.normal_authorization
        mapping = input.authoritative_mapping
        recovery = input.recovery_authorization_report
        values = _Values(
            attempt_id=binding.attempt_id,
            output_asset_id=binding.output_asset_id,
            project_id=binding.project_id,
            page_id=binding.page_id,
            target_page_reference=binding.target_page_reference,
            provider_reference=binding.provider_reference,
        )
        findings: list[RecoveryExternalApplicationFindingDTO] = []

        if recovery.status != "ready" or recovery.ready is not True:
            findings.append(_finding("RECOVERY_AUTHORIZATION_NOT_READY", values))
        request, proposal = _recovery_chain(recovery)
        if request is None or proposal is None:
            findings.append(_finding("RECOVERY_INPUT_CHAIN_INVALID", values))
        else:
            if (
                request.recovery_proposal_id != mapping.recovery_proposal_id
                or request.recovery_request_id != mapping.recovery_request_id
                or proposal.proposal_id != mapping.recovery_proposal_id
                or proposal.target_page_id != mapping.recovery_target_page_id
                or proposal.target_panel_id != mapping.recovery_target_panel_id
            ):
                findings.append(_finding("RECOVERY_TARGET_MAPPING_MISMATCH", values))
            if binding.attempt_id == proposal.source_attempt_id:
                findings.append(_finding("RECOVERY_ATTEMPT_ID_NOT_DISTINCT", values))
            if binding.output_asset_id == proposal.source_output_asset_id:
                findings.append(_finding("RECOVERY_OUTPUT_ASSET_ID_NOT_DISTINCT", values))

        if binding.status != "eligible" or binding.eligible is not True:
            findings.append(_finding("NORMAL_BINDING_NOT_ELIGIBLE", values))
        if (
            binding.project_id != mapping.project_id
            or binding.page_id != mapping.page_id
            or binding.target_page_reference != mapping.target_page_reference
        ):
            findings.append(_finding("NORMAL_BINDING_TARGET_MISMATCH", values))
        if (
            authorization.attempt_id != binding.attempt_id
            or authorization.provider_reference != binding.provider_reference
            or authorization.project_id != binding.project_id
            or authorization.page_id != binding.page_id
            or authorization.target_page_reference != binding.target_page_reference
            or authorization.source_state != "PromptBuilt"
            or authorization.target_state != "Generated"
        ):
            findings.append(_finding("NORMAL_AUTHORIZATION_BINDING_MISMATCH", values))
        if request is not None and request_provider(recovery) != binding.provider_reference:
            findings.append(_finding("RECOVERY_PROVIDER_BINDING_MISMATCH", values))
        if not _authorization_records_agree(recovery, mapping, binding.provider_reference):
            findings.append(_finding("RECOVERY_AUTHORIZATION_BINDING_MISMATCH", values))

        ordered = tuple(sorted(findings, key=_finding_key))
        return RecoveryExternalApplicationBridgeReport(
            attempt_id=values.attempt_id,
            output_asset_id=values.output_asset_id,
            project_id=values.project_id,
            page_id=values.page_id,
            target_page_reference=values.target_page_reference,
            provider_reference=values.provider_reference,
            findings=ordered,
            status="delegated" if not ordered else "blocked",
            delegatable=not ordered,
        )


@dataclass(frozen=True, slots=True)
class _Values:
    attempt_id: str
    output_asset_id: str
    project_id: str
    page_id: str
    target_page_reference: str
    provider_reference: str


def _recovery_chain(
    report: RecoveryExecutionAuthorizationValidationReport,
) -> tuple[RecoveryStructuredGenerationRequestDTO | None, GenerationRecoveryProposalDTO | None]:
    """Extract only already-validated Recovery references without revalidation."""

    try:
        readiness = report.recovery_readiness_report
        request = readiness.input.recovery_request_validation_report.request
        proposals = readiness.input.recovery_proposal_validation_report.proposals
    except AttributeError:
        return None, None
    matching = tuple(item for item in proposals if item.proposal_id == request.recovery_proposal_id)
    return (request, matching[0]) if len(matching) == 1 else (request, None)


def request_provider(report: RecoveryExecutionAuthorizationValidationReport) -> str:
    """Return the already-validated provider reference, never a selected provider."""

    return report.recovery_readiness_report.input.provider_reference


def _authorization_records_agree(
    report: RecoveryExecutionAuthorizationValidationReport,
    mapping: RecoveryAuthoritativeWorkflowPageMappingDTO,
    provider_reference: str,
) -> bool:
    records = report.authorization_records
    return bool(records) and all(
        item.recovery_proposal_id == mapping.recovery_proposal_id
        and item.recovery_request_id == mapping.recovery_request_id
        and item.provider_reference == provider_reference
        for item in records
    )


def _finding(code: str, values: _Values) -> RecoveryExternalApplicationFindingDTO:
    return RecoveryExternalApplicationFindingDTO(
        code=code,
        status="blocked",
        message=code.replace("_", " ").lower(),
        attempt_id=values.attempt_id,
        output_asset_id=values.output_asset_id,
        project_id=values.project_id,
        page_id=values.page_id,
        target_page_reference=values.target_page_reference,
        provider_reference=values.provider_reference,
    )


def _finding_key(
    finding: RecoveryExternalApplicationFindingDTO,
) -> tuple[str, str, str, str, str, str, str]:
    return (
        finding.code,
        finding.attempt_id,
        finding.output_asset_id,
        finding.project_id,
        finding.page_id,
        finding.target_page_reference,
        finding.provider_reference,
    )


def _logical_reference(value: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("logical reference must be nonblank")
    if value.startswith(("/", "\\")) or "://" in value or "@" in value:
        raise ValueError("logical reference must not be a path, URL, or email")
    return value
