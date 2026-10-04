"""Internal read-only validation for caller-supplied recovery proposals."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from typing import Literal

from pydantic import ConfigDict, field_validator

from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_generation_evidence import (
    GenerationEvidenceEnvelopeDTO,
    GenerationEvidenceValidationReport,
)
from manga_director.production.next_generation_human_review_decision import (
    HumanReviewDecisionRecordDTO,
    HumanReviewDecisionValidationReport,
)

FindingStatus = Literal["blocked", "needs_review"]
ReportStatus = Literal["ready", "needs_review", "blocked"]
_CHANGE_SCOPES = frozenset({"prompt", "composition", "parameters"})
_PRESERVATION_SCOPES = frozenset(
    {
        "identity_bindings",
        "reference_asset_ids",
        "generation_input_reference",
        "provider_configuration",
        "seed",
        "output_provenance",
    }
)
_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\\\/]")


class _RecoveryModel(DirectorModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class GenerationRecoveryProposalDTO(_RecoveryModel):
    proposal_id: str
    source_decision_id: str
    source_attempt_id: str
    source_output_asset_id: str
    source_provenance_reference: str
    target_page_id: str
    target_panel_id: str
    requested_change_scopes: tuple[str, ...]
    preservation_scopes: tuple[str, ...]
    authorization_required: bool

    @field_validator(
        "proposal_id",
        "source_decision_id",
        "source_attempt_id",
        "source_output_asset_id",
        "source_provenance_reference",
        "target_page_id",
        "target_panel_id",
    )
    @classmethod
    def _validate_reference(cls, value: str) -> str:
        return _logical_reference(value)


class GenerationRecoveryProposalFindingDTO(_RecoveryModel):
    code: str
    status: FindingStatus
    message: str
    proposal_id: str = ""


class GenerationRecoveryProposalValidationReport(_RecoveryModel):
    proposals: tuple[GenerationRecoveryProposalDTO, ...] = ()
    findings: tuple[GenerationRecoveryProposalFindingDTO, ...] = ()
    status: ReportStatus
    ready: bool
    analysis_only: Literal[True] = True


class GenerationRecoveryProposalValidationService:
    """Validate proposal evidence without authorizing or executing recovery."""

    def validate(
        self,
        proposals: Sequence[GenerationRecoveryProposalDTO] = (),
        *,
        human_review_decision_validation_report: HumanReviewDecisionValidationReport | None = None,
        generation_evidence_validation_report: GenerationEvidenceValidationReport | None = None,
    ) -> GenerationRecoveryProposalValidationReport:
        canonical = tuple(sorted(proposals, key=lambda item: item.proposal_id))
        findings: list[GenerationRecoveryProposalFindingDTO] = []
        for proposal_id in _duplicates(item.proposal_id for item in canonical):
            findings.append(_finding("DUPLICATE_PROPOSAL_ID", "blocked", proposal_id))
        for proposal in canonical:
            _validate_scopes(proposal, findings)
            _validate_authorization(proposal, findings)
            source = _source_decision(proposal, human_review_decision_validation_report, findings)
            _validate_generation(proposal, generation_evidence_validation_report, findings)
            if source is not None and _has_conflicting_source(source, human_review_decision_validation_report):
                findings.append(_finding("CONFLICTING_SOURCE_DECISIONS", "blocked", proposal.proposal_id))
            findings.append(_finding("AUTHORIZATION_REQUIRED", "needs_review", proposal.proposal_id))
        ordered = tuple(sorted(findings, key=lambda item: (item.code, item.proposal_id, item.message)))
        status: ReportStatus = "blocked" if any(item.status == "blocked" for item in ordered) else "needs_review"
        return GenerationRecoveryProposalValidationReport(
            proposals=canonical, findings=ordered, status=status, ready=False
        )


def _logical_reference(value: str) -> str:
    if not value or value != value.strip() or any(char.isspace() for char in value):
        raise ValueError("reference must be a nonblank logical value")
    if value.startswith(("/", "\\")) or "://" in value or _WINDOWS_ABSOLUTE_PATH.match(value):
        raise ValueError("reference must not be a path or URL")
    return value


def _validate_scopes(
    proposal: GenerationRecoveryProposalDTO, findings: list[GenerationRecoveryProposalFindingDTO]
) -> None:
    if not proposal.requested_change_scopes or any(
        item not in _CHANGE_SCOPES for item in proposal.requested_change_scopes
    ):
        findings.append(_finding("INVALID_CHANGE_SCOPE", "blocked", proposal.proposal_id))
    if not proposal.preservation_scopes or any(
        item not in _PRESERVATION_SCOPES for item in proposal.preservation_scopes
    ):
        findings.append(_finding("INVALID_PRESERVATION_SCOPE", "blocked", proposal.proposal_id))
    if "identity_bindings" not in proposal.preservation_scopes:
        findings.append(_finding("MISSING_IDENTITY_BINDING_PRESERVATION", "blocked", proposal.proposal_id))


def _validate_authorization(
    proposal: GenerationRecoveryProposalDTO, findings: list[GenerationRecoveryProposalFindingDTO]
) -> None:
    if not proposal.authorization_required:
        findings.append(_finding("AUTHORIZATION_REQUIRED_MUST_BE_TRUE", "blocked", proposal.proposal_id))


def _source_decision(
    proposal: GenerationRecoveryProposalDTO,
    report: HumanReviewDecisionValidationReport | None,
    findings: list[GenerationRecoveryProposalFindingDTO],
) -> HumanReviewDecisionRecordDTO | None:
    matching = tuple(item for item in report.decisions if item.decision_id == proposal.source_decision_id) if report else ()
    if len(matching) != 1:
        findings.append(_finding("MISSING_OR_AMBIGUOUS_SOURCE_DECISION", "blocked", proposal.proposal_id))
        return None
    source = matching[0]
    if source.decision != "change_requested":
        findings.append(_finding("SOURCE_DECISION_NOT_CHANGE_REQUESTED", "blocked", proposal.proposal_id))
    return source


def _has_conflicting_source(
    source: HumanReviewDecisionRecordDTO, report: HumanReviewDecisionValidationReport | None
) -> bool:
    if report is None:
        return False
    decisions = [
        item
        for item in report.decisions
        if (item.qa_report_reference, item.target_type, item.target_reference)
        == (source.qa_report_reference, source.target_type, source.target_reference)
    ]
    return len({item.decision for item in decisions}) > 1


def _validate_generation(
    proposal: GenerationRecoveryProposalDTO,
    report: GenerationEvidenceValidationReport | None,
    findings: list[GenerationRecoveryProposalFindingDTO],
) -> None:
    matching = tuple(item for item in report.envelopes if item.attempt_id == proposal.source_attempt_id) if report else ()
    if len(matching) != 1:
        findings.append(_finding("MISSING_OR_AMBIGUOUS_GENERATION_EVIDENCE", "blocked", proposal.proposal_id))
        return
    envelope: GenerationEvidenceEnvelopeDTO = matching[0]
    if (
        envelope.output.output_asset_id != proposal.source_output_asset_id
        or envelope.provenance_reference != proposal.source_provenance_reference
    ):
        findings.append(_finding("GENERATION_TARGET_EVIDENCE_CONFLICT", "blocked", proposal.proposal_id))


def _finding(code: str, status: FindingStatus, proposal_id: str) -> GenerationRecoveryProposalFindingDTO:
    return GenerationRecoveryProposalFindingDTO(
        code=code, status=status, message=code.replace("_", " ").lower(), proposal_id=proposal_id
    )


def _duplicates(values: Iterable[str]) -> tuple[str, ...]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return tuple(sorted(value for value, count in counts.items() if count > 1))
