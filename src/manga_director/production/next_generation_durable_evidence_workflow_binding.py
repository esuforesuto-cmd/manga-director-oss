"""Internal read-only validation for future durable-Evidence workflow application.

This boundary only determines eligibility.  It never applies a workflow
transition, accesses an asset, or changes any historical Evidence record.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal, cast

from pydantic import ConfigDict, field_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_attempt_to_evidence_binding import (
    AttemptToEvidenceBindingReport,
)
from manga_director.production.next_generation_attempt_to_evidence_construction import (
    AttemptToEvidenceConstructionReport,
)
from manga_director.production.next_generation_generation_evidence import (
    GenerationEvidenceEnvelopeDTO,
    GenerationEvidenceValidationReport,
)
from manga_director.production.next_generation_generation_evidence_persistence import (
    GenerationEvidencePersistenceReport,
    GenerationEvidenceStoreLookupResult,
    GenerationEvidenceStorePort,
)
from manga_director.workflow.contracts import WorkflowContext

FindingStatus = Literal["blocked"]
ReportStatus = Literal["eligible", "blocked"]

_SOURCE_STATE = "PromptBuilt"
_TARGET_STATE = "Generated"
_WINDOWS_ABSOLUTE_PATH = ("/", "\\")


class _DurableEvidenceWorkflowBindingModel(DirectorModel):
    """Private base for closed immutable validation-only DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class WorkflowApplicationAuthorizationDTO(_DurableEvidenceWorkflowBindingModel):
    """Caller/human authorization for one future page-level workflow application."""

    authorization_id: str
    authorizer_id: str
    authorized_at: datetime
    attempt_id: str
    provider_reference: str
    project_id: str
    page_id: str
    target_page_reference: str
    source_state: Literal["PromptBuilt"]
    target_state: Literal["Generated"]

    @field_validator(
        "authorization_id",
        "authorizer_id",
        "attempt_id",
        "provider_reference",
        "project_id",
        "page_id",
        "target_page_reference",
    )
    @classmethod
    def _validate_logical_reference(cls, value: str) -> str:
        return _logical_reference(value)

    @field_validator("authorized_at")
    @classmethod
    def _require_timezone_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("authorized_at must be timezone-aware")
        return value


class AuthoritativeWorkflowPageMappingDTO(_DurableEvidenceWorkflowBindingModel):
    """Trusted exact mapping from a Next Generation target to one V6 page context."""

    project_id: str
    page_id: str
    target_page_reference: str

    @field_validator("project_id", "page_id", "target_page_reference")
    @classmethod
    def _validate_logical_reference(cls, value: str) -> str:
        return _logical_reference(value)


class DurableEvidenceWorkflowBindingFindingDTO(_DurableEvidenceWorkflowBindingModel):
    """One deterministic redacted eligibility finding."""

    code: str
    status: FindingStatus
    message: str
    attempt_id: str = ""
    provider_reference: str = ""
    output_asset_id: str = ""
    project_id: str = ""
    page_id: str = ""
    target_page_reference: str = ""


class DurableEvidenceWorkflowBindingReport(_DurableEvidenceWorkflowBindingModel):
    """Immutable read-only future-application eligibility result."""

    attempt_id: str = ""
    provider_reference: str = ""
    output_asset_id: str = ""
    project_id: str = ""
    page_id: str = ""
    target_page_reference: str = ""
    findings: tuple[DurableEvidenceWorkflowBindingFindingDTO, ...] = ()
    status: ReportStatus
    eligible: bool
    analysis_only: Literal[True] = True
    workflow_transition_performed: Literal[False] = False
    state_machine_action: Literal[False] = False
    event_published: Literal[False] = False
    asset_retrieved: Literal[False] = False
    byte_accessed: Literal[False] = False
    evidence_mutated: Literal[False] = False
    ledger_persisted: Literal[False] = False


class DurableEvidenceWorkflowBindingValidationService:
    """Validate one future workflow-application candidate without applying it."""

    def validate(
        self,
        authorization: WorkflowApplicationAuthorizationDTO | None,
        page_mapping: AuthoritativeWorkflowPageMappingDTO | None,
        workflow_context: WorkflowContext | None,
        persistence_report: GenerationEvidencePersistenceReport | None,
        evidence_store: GenerationEvidenceStorePort | None,
        construction_report: AttemptToEvidenceConstructionReport | None,
    ) -> DurableEvidenceWorkflowBindingReport:
        """Return a deterministic redacted eligibility report without side effects."""

        values = _values(authorization, page_mapping, workflow_context, persistence_report, construction_report)
        findings: list[DurableEvidenceWorkflowBindingFindingDTO] = []
        if authorization is None:
            findings.append(_finding("WORKFLOW_APPLICATION_AUTHORIZATION_MISSING", values))
        if page_mapping is None:
            findings.append(_finding("AUTHORITATIVE_PAGE_MAPPING_MISSING", values))
        if workflow_context is None:
            findings.append(_finding("WORKFLOW_CONTEXT_MISSING", values))
        if persistence_report is None:
            findings.append(_finding("EVIDENCE_PERSISTENCE_REPORT_MISSING", values))
        if construction_report is None:
            findings.append(_finding("EVIDENCE_CONSTRUCTION_REPORT_MISSING", values))

        if authorization is not None and page_mapping is not None and workflow_context is not None:
            findings.extend(_workflow_binding_findings(authorization, page_mapping, workflow_context, values))
        if construction_report is not None:
            chain, chain_findings = _construction_chain(construction_report, values)
            findings.extend(chain_findings)
        else:
            chain = None
        if persistence_report is not None and construction_report is not None:
            findings.extend(_persistence_findings(persistence_report, construction_report, values))

        if chain is not None and authorization is not None and page_mapping is not None:
            findings.extend(_chain_binding_findings(chain, authorization, page_mapping, values))

        if evidence_store is None:
            findings.append(_finding("DURABLE_EVIDENCE_STORE_MISSING", values))
        elif persistence_report is not None and construction_report is not None:
            findings.extend(
                _lookup_findings(evidence_store, construction_report, persistence_report, values)
            )

        ordered_findings = tuple(sorted(findings, key=_finding_key))
        return DurableEvidenceWorkflowBindingReport(
            attempt_id=values.attempt_id,
            provider_reference=values.provider_reference,
            output_asset_id=values.output_asset_id,
            project_id=values.project_id,
            page_id=values.page_id,
            target_page_reference=values.target_page_reference,
            findings=ordered_findings,
            status="eligible" if not ordered_findings else "blocked",
            eligible=not ordered_findings,
        )


class _Values:
    """Private safe values used to keep findings bounded and redacted."""

    def __init__(
        self,
        attempt_id: str = "",
        provider_reference: str = "",
        output_asset_id: str = "",
        project_id: str = "",
        page_id: str = "",
        target_page_reference: str = "",
    ) -> None:
        self.attempt_id = attempt_id
        self.provider_reference = provider_reference
        self.output_asset_id = output_asset_id
        self.project_id = project_id
        self.page_id = page_id
        self.target_page_reference = target_page_reference


class _ConstructionChain:
    """Private chain-derived values; no source report is changed."""

    def __init__(
        self,
        request: object,
        registration: Any,
        evidence: GenerationEvidenceEnvelopeDTO,
        validation: GenerationEvidenceValidationReport,
        binding: AttemptToEvidenceBindingReport,
    ) -> None:
        self.request = request
        self.registration = registration
        self.evidence = evidence
        self.validation = validation
        self.binding = binding


def _values(
    authorization: WorkflowApplicationAuthorizationDTO | None,
    page_mapping: AuthoritativeWorkflowPageMappingDTO | None,
    workflow_context: WorkflowContext | None,
    persistence_report: GenerationEvidencePersistenceReport | None,
    construction_report: AttemptToEvidenceConstructionReport | None,
) -> _Values:
    evidence = getattr(construction_report, "generation_evidence", None)
    return _Values(
        attempt_id=_safe_value(
            getattr(authorization, "attempt_id", "")
            or getattr(persistence_report, "attempt_id", "")
            or getattr(construction_report, "attempt_id", "")
        ),
        provider_reference=_safe_value(
            getattr(authorization, "provider_reference", "")
            or getattr(construction_report, "provider_reference", "")
        ),
        output_asset_id=_safe_value(getattr(getattr(evidence, "output", None), "output_asset_id", "")),
        project_id=_safe_value(
            getattr(page_mapping, "project_id", "") or _context_value(workflow_context, "project_id")
        ),
        page_id=_safe_value(
            getattr(page_mapping, "page_id", "") or _context_value(workflow_context, "page_id")
        ),
        target_page_reference=_safe_value(
            getattr(page_mapping, "target_page_reference", "")
            or getattr(authorization, "target_page_reference", "")
        ),
    )


def _workflow_binding_findings(
    authorization: WorkflowApplicationAuthorizationDTO,
    mapping: AuthoritativeWorkflowPageMappingDTO,
    context: WorkflowContext,
    values: _Values,
) -> list[DurableEvidenceWorkflowBindingFindingDTO]:
    findings: list[DurableEvidenceWorkflowBindingFindingDTO] = []
    if authorization.source_state != _SOURCE_STATE or _context_state(context) != _SOURCE_STATE:
        findings.append(_finding("WORKFLOW_SOURCE_STATE_MISMATCH", values))
    if authorization.target_state != _TARGET_STATE:
        findings.append(_finding("WORKFLOW_TARGET_STATE_MISMATCH", values))
    context_project_id = _context_value(context, "project_id")
    context_page_id = _context_value(context, "page_id")
    if not context_project_id or not context_page_id:
        findings.append(_finding("WORKFLOW_CONTEXT_IDENTITY_INVALID", values))
    if (
        authorization.project_id != mapping.project_id
        or authorization.page_id != mapping.page_id
        or authorization.target_page_reference != mapping.target_page_reference
        or context_project_id != mapping.project_id
        or context_page_id != mapping.page_id
    ):
        findings.append(_finding("AUTHORITATIVE_PAGE_MAPPING_MISMATCH", values))
    return findings


def _construction_chain(
    report: AttemptToEvidenceConstructionReport,
    values: _Values,
) -> tuple[_ConstructionChain | None, list[DurableEvidenceWorkflowBindingFindingDTO]]:
    findings: list[DurableEvidenceWorkflowBindingFindingDTO] = []
    evidence = getattr(report, "generation_evidence", None)
    validation = getattr(report, "generation_evidence_validation_report", None)
    binding = getattr(report, "attempt_to_evidence_binding_report", None)
    registration = getattr(report, "output_asset_registration_report", None)
    if (
        report.constructed is not True
        or report.bound is not True
        or report.ready is not True
        or report.status != "ready"
        or not isinstance(evidence, GenerationEvidenceEnvelopeDTO)
        or not isinstance(validation, GenerationEvidenceValidationReport)
        or not isinstance(binding, AttemptToEvidenceBindingReport)
        or registration is None
    ):
        return None, [_finding("MALFORMED_OR_UNREADY_EVIDENCE_CHAIN", values)]
    if validation.status != "ready" or validation.ready is not True:
        findings.append(_finding("EVIDENCE_VALIDATION_NOT_READY", values))
    matching_evidence = tuple(
        item for item in validation.envelopes if item.attempt_id == report.attempt_id
    )
    if len(matching_evidence) != 1 or not _same_evidence(matching_evidence[0], evidence):
        findings.append(_finding("EVIDENCE_VALIDATION_BINDING_MISMATCH", values))
    if (
        binding.status != "ready"
        or binding.ready is not True
        or binding.bound is not True
        or binding.attempt_id != report.attempt_id
        or binding.generation_evidence_validation_report != validation
        or binding.output_asset_registration_report != registration
    ):
        findings.append(_finding("EVIDENCE_BINDING_NOT_READY", values))
    request = _request_from_registration(registration)
    if request is None:
        findings.append(_finding("MALFORMED_NESTED_REPORT_CHAIN", values))
        return None, findings
    if (
        getattr(request, "request_id", None) != report.request_id
        or evidence.attempt_id != report.attempt_id
        or getattr(registration, "attempt_id", None) != report.attempt_id
    ):
        findings.append(_finding("ATTEMPT_BINDING_MISMATCH", values))
    return _ConstructionChain(request, registration, evidence, validation, binding), findings


def _chain_binding_findings(
    chain: _ConstructionChain,
    authorization: WorkflowApplicationAuthorizationDTO,
    mapping: AuthoritativeWorkflowPageMappingDTO,
    values: _Values,
) -> list[DurableEvidenceWorkflowBindingFindingDTO]:
    findings: list[DurableEvidenceWorkflowBindingFindingDTO] = []
    request = chain.request
    registration = chain.registration
    if authorization.attempt_id != chain.evidence.attempt_id:
        findings.append(_finding("ATTEMPT_BINDING_MISMATCH", values))
    if (
        authorization.provider_reference != getattr(registration, "provider_reference", None)
        or authorization.provider_reference != _construction_provider(chain)
    ):
        findings.append(_finding("PROVIDER_BINDING_MISMATCH", values))
    if getattr(request, "target_page_reference", None) != mapping.target_page_reference:
        findings.append(_finding("TARGET_PAGE_REFERENCE_MISMATCH", values))
    if getattr(request, "target_panel_reference", None) is not None:
        findings.append(_finding("PANEL_TARGET_UNSUPPORTED", values))
    return findings


def _persistence_findings(
    persistence: GenerationEvidencePersistenceReport,
    construction: AttemptToEvidenceConstructionReport,
    values: _Values,
) -> list[DurableEvidenceWorkflowBindingFindingDTO]:
    evidence = getattr(construction, "generation_evidence", None)
    if (
        persistence.status != "persisted"
        or persistence.persisted is not True
        or persistence.persistence_performed is not True
        or persistence.attempt_id != construction.attempt_id
        or not isinstance(persistence.generation_evidence, GenerationEvidenceEnvelopeDTO)
        or not isinstance(evidence, GenerationEvidenceEnvelopeDTO)
    ):
        return [_finding("EVIDENCE_PERSISTENCE_NOT_SUCCESSFUL", values)]
    if not _same_evidence(persistence.generation_evidence, evidence):
        return [_finding("PERSISTED_EVIDENCE_MISMATCH", values)]
    return []


def _lookup_findings(
    store: GenerationEvidenceStorePort,
    construction: AttemptToEvidenceConstructionReport,
    persistence: GenerationEvidencePersistenceReport,
    values: _Values,
) -> list[DurableEvidenceWorkflowBindingFindingDTO]:
    attempt_id = _safe_value(getattr(construction, "attempt_id", ""))
    if not attempt_id:
        return [_finding("ATTEMPT_BINDING_MISMATCH", values)]
    try:
        result = store.lookup(attempt_id)
    except Exception:
        return [_finding("DURABLE_EVIDENCE_LOOKUP_FAILED", values)]
    if not isinstance(result, GenerationEvidenceStoreLookupResult):
        return [_finding("DURABLE_EVIDENCE_LOOKUP_INVALID", values)]
    if result.outcome == "missing":
        return [_finding("DURABLE_EVIDENCE_MISSING", values)]
    if result.outcome != "found" or result.attempt_id != attempt_id:
        return [_finding("DURABLE_EVIDENCE_CORRUPT", values)]
    evidence = result.generation_evidence
    persisted = persistence.generation_evidence
    constructed = construction.generation_evidence
    if (
        result.evidence_status != "ready"
        or not isinstance(evidence, GenerationEvidenceEnvelopeDTO)
        or not isinstance(persisted, GenerationEvidenceEnvelopeDTO)
        or not isinstance(constructed, GenerationEvidenceEnvelopeDTO)
    ):
        return [_finding("DURABLE_EVIDENCE_CORRUPT", values)]
    if not _same_evidence(evidence, persisted) or not _same_evidence(evidence, constructed):
        return [_finding("DURABLE_EVIDENCE_MISMATCH", values)]
    if evidence.output.output_asset_id != constructed.output.output_asset_id:
        return [_finding("OUTPUT_ASSET_BINDING_MISMATCH", values)]
    return []


def _request_from_registration(registration: Any) -> object | None:
    try:
        invocation = registration.provider_invocation_report
        resolution = invocation.secure_execution_input_resolution_report
        envelope_report = resolution.authorized_execution_envelope_validation_report
        execution_authorization = envelope_report.execution_authorization_validation_report
        readiness = execution_authorization.readiness_report
        request_report = readiness.input.request_validation_report
        request = request_report.request
    except (AttributeError, TypeError):
        return None
    if request_report.status != "ready" or request_report.ready is not True:
        return None
    return cast(object, request)


def _construction_provider(chain: _ConstructionChain) -> str | None:
    try:
        provider_reference = chain.registration.provider_invocation_report.provider_reference
    except AttributeError:
        return None
    return provider_reference if isinstance(provider_reference, str) else None


def _same_evidence(left: GenerationEvidenceEnvelopeDTO, right: GenerationEvidenceEnvelopeDTO) -> bool:
    return _canonical_json(left) == _canonical_json(right)


def _canonical_json(evidence: GenerationEvidenceEnvelopeDTO) -> str:
    return json.dumps(
        evidence.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


def _context_value(context: WorkflowContext | None, key: str) -> str:
    if context is None or not isinstance(context.page, dict):
        return ""
    return _safe_value(context.page.get(key, ""))


def _context_state(context: WorkflowContext) -> str:
    state = getattr(context, "state", None)
    return _safe_value(getattr(state, "value", state))


def _finding(code: str, values: _Values) -> DurableEvidenceWorkflowBindingFindingDTO:
    return DurableEvidenceWorkflowBindingFindingDTO(
        code=code,
        status="blocked",
        message=code.replace("_", " ").lower(),
        attempt_id=values.attempt_id,
        provider_reference=values.provider_reference,
        output_asset_id=values.output_asset_id,
        project_id=values.project_id,
        page_id=values.page_id,
        target_page_reference=values.target_page_reference,
    )


def _finding_key(
    finding: DurableEvidenceWorkflowBindingFindingDTO,
) -> tuple[str, str, str, str, str, str, str]:
    return (
        finding.code,
        finding.attempt_id,
        finding.provider_reference,
        finding.output_asset_id,
        finding.project_id,
        finding.page_id,
        finding.target_page_reference,
    )


def _logical_reference(value: str) -> str:
    if not value or value != value.strip() or any(character.isspace() for character in value):
        raise ValueError("workflow application reference must be a nonblank logical reference")
    if value.startswith(_WINDOWS_ABSOLUTE_PATH) or "://" in value or "@" in value:
        raise ValueError("workflow application reference must not be a path, URL, or email")
    return value


def _safe_value(value: object) -> str:
    return value if isinstance(value, str) and _is_logical_reference(value) else ""


def _is_logical_reference(value: str) -> bool:
    return bool(value) and value == value.strip() and not value.startswith(_WINDOWS_ABSOLUTE_PATH) and "://" not in value and "@" not in value and not any(character.isspace() for character in value)
