"""Internal advisory readiness for one explicit human visual QA judgment.

This service composes existing immutable evidence reports.  It performs no
asset access, persistence, provider execution, workflow transition, or Page
approval.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, Field, field_validator

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.production.next_generation_attempt_to_evidence_binding import (
    AttemptToEvidenceBindingReport,
)
from manga_director.production.next_generation_character_identity import (
    IdentityValidationReport,
)
from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    DurableEvidenceWorkflowBindingReport,
)
from manga_director.production.next_generation_visual_continuity_qa import (
    VisualContinuityQAReport,
    VisualContinuityQAService,
)
from manga_director.production.reliability import WorkflowConsistencyReport

ReadinessStatus = Literal["ready", "needs_review", "blocked"]
FindingStatus = Literal["needs_review", "blocked"]
HumanVisualOutcome = Literal["acceptable", "needs_review", "blocked", "not_applicable"]
OverallHumanJudgment = Literal[
    "acceptable_for_approval_consideration",
    "further_review_required",
    "blocked",
]
HumanVisualCriterion = Literal[
    "character_identity",
    "face",
    "costume",
    "props",
    "pose",
    "gaze",
    "emotion",
    "screen_direction",
    "location",
    "time",
    "composition",
    "panel_intent",
    "visible_corruption",
    "truncation",
    "watermark",
    "unsafe_content",
    "unintended_text",
    "continuity_comparison",
]

_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\\\/]")
_SECRET_LIKE_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "endpoint",
    "password",
    "secret",
    "token",
)
_REQUIRED_CRITERIA: tuple[HumanVisualCriterion, ...] = (
    "character_identity",
    "face",
    "costume",
    "props",
    "pose",
    "gaze",
    "emotion",
    "screen_direction",
    "location",
    "time",
    "composition",
    "panel_intent",
    "visible_corruption",
    "truncation",
    "watermark",
    "unsafe_content",
    "unintended_text",
    "continuity_comparison",
)
_OPTIONAL_CRITERIA = frozenset({"props", "continuity_comparison"})


class _ApprovalReadinessModel(DirectorModel):
    """Private base for closed, immutable internal DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class ApprovalReadinessScopeDTO(_ApprovalReadinessModel):
    """Exact Page and generation evidence chain selected by the caller."""

    project_id: str
    page_id: str
    page_number: int = Field(ge=1)
    target_page_reference: str
    attempt_id: str
    output_asset_id: str
    provenance_reference: str
    qa_report_reference: str

    @field_validator(
        "project_id",
        "page_id",
        "target_page_reference",
        "attempt_id",
        "output_asset_id",
        "provenance_reference",
        "qa_report_reference",
    )
    @classmethod
    def _validate_reference(cls, value: str) -> str:
        return _logical_reference(value, "approval-readiness reference")


class HumanVisualChecklistDecisionDTO(_ApprovalReadinessModel):
    """One explicit human result for a mandatory visual criterion."""

    criterion: HumanVisualCriterion
    outcome: HumanVisualOutcome
    rationale: str = Field(min_length=1, max_length=500)

    @field_validator("rationale")
    @classmethod
    def _validate_rationale(cls, value: str) -> str:
        return _safe_rationale(value)


class HumanVisualJudgmentDTO(_ApprovalReadinessModel):
    """Caller-supplied human judgment bound to one exact output."""

    review_id: str
    project_id: str
    page_id: str
    attempt_id: str
    output_asset_id: str
    provenance_reference: str
    qa_report_reference: str
    reviewer_id: str
    reviewed_at: datetime
    checklist: tuple[HumanVisualChecklistDecisionDTO, ...]
    overall_judgment: OverallHumanJudgment
    rationale: str = Field(min_length=1, max_length=500)
    policy_reference: str | None = None
    prior_review_reference: str | None = None

    @field_validator(
        "review_id",
        "project_id",
        "page_id",
        "attempt_id",
        "output_asset_id",
        "provenance_reference",
        "qa_report_reference",
        "reviewer_id",
        "policy_reference",
        "prior_review_reference",
    )
    @classmethod
    def _validate_reference(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _logical_reference(value, "human visual judgment reference")

    @field_validator("reviewed_at")
    @classmethod
    def _require_timezone_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reviewed_at must be timezone-aware")
        return value

    @field_validator("rationale")
    @classmethod
    def _validate_rationale(cls, value: str) -> str:
        return _safe_rationale(value)


class ApprovalReadinessFindingDTO(_ApprovalReadinessModel):
    """One deterministic finding without image data or private payloads."""

    code: str
    status: FindingStatus
    message: str
    criterion: str = ""


class HumanVisualQAApprovalReadinessReport(_ApprovalReadinessModel):
    """Canonical advisory result that cannot approve or transition a Page."""

    scope: ApprovalReadinessScopeDTO
    persisted_page_state: PageState
    human_judgment: HumanVisualJudgmentDTO | None = None
    findings: tuple[ApprovalReadinessFindingDTO, ...] = ()
    missing_prerequisites: tuple[str, ...] = ()
    status: ReadinessStatus
    ready: bool
    analysis_only: Literal[True] = True


class HumanVisualQAApprovalReadinessService:
    """Derive advisory readiness from supplied immutable evidence."""

    def assess(
        self,
        scope: ApprovalReadinessScopeDTO,
        attempt_binding_report: AttemptToEvidenceBindingReport,
        workflow_page_binding_report: DurableEvidenceWorkflowBindingReport,
        workflow_consistency_report: WorkflowConsistencyReport,
        visual_qa_report: VisualContinuityQAReport,
        identity_validation_report: IdentityValidationReport | None = None,
        human_judgment: HumanVisualJudgmentDTO | None = None,
    ) -> HumanVisualQAApprovalReadinessReport:
        """Return a deterministic fail-closed result without side effects."""

        canonical_judgment = _canonical_judgment(human_judgment)
        findings: list[ApprovalReadinessFindingDTO] = []
        _append_persisted_page_findings(scope, workflow_consistency_report, findings)
        _append_attempt_binding_findings(scope, attempt_binding_report, findings)
        _append_workflow_page_binding_findings(scope, workflow_page_binding_report, findings)
        _append_visual_qa_findings(
            scope,
            visual_qa_report,
            attempt_binding_report,
            identity_validation_report,
            findings,
        )
        _append_human_judgment_findings(scope, canonical_judgment, findings)
        ordered_findings = tuple(sorted(findings, key=_finding_key))
        status = _readiness_status(ordered_findings)
        return HumanVisualQAApprovalReadinessReport(
            scope=scope,
            persisted_page_state=workflow_consistency_report.current_state,
            human_judgment=canonical_judgment,
            findings=ordered_findings,
            missing_prerequisites=tuple(
                sorted({item.code for item in ordered_findings if item.status == "needs_review"})
            ),
            status=status,
            ready=status == "ready",
        )


def _logical_reference(value: str, label: str) -> str:
    if not value or value != value.strip() or any(character.isspace() for character in value):
        raise ValueError(f"{label} must be a nonblank logical reference")
    if value.startswith(("/", "\\")) or "://" in value or _WINDOWS_ABSOLUTE_PATH.match(value):
        raise ValueError(f"{label} must not be a path or URL")
    if "@" in value:
        raise ValueError(f"{label} must not contain an email address")
    if any(part in value.lower() for part in _SECRET_LIKE_PARTS):
        raise ValueError(f"{label} must not contain a secret-like value")
    if len(value) > 200:
        raise ValueError(f"{label} must not exceed 200 characters")
    return value


def _safe_rationale(value: str) -> str:
    if value != value.strip() or not value.strip():
        raise ValueError("rationale must be concise nonblank text")
    if "://" in value or _WINDOWS_ABSOLUTE_PATH.search(value) or "@" in value:
        raise ValueError("rationale must not contain a path, URL, or email address")
    if any(part in value.lower() for part in _SECRET_LIKE_PARTS):
        raise ValueError("rationale must not contain a secret-like value")
    return value


def _canonical_judgment(
    judgment: HumanVisualJudgmentDTO | None,
) -> HumanVisualJudgmentDTO | None:
    if judgment is None:
        return None
    checklist = tuple(
        sorted(judgment.checklist, key=lambda item: (item.criterion, item.outcome, item.rationale))
    )
    return judgment.model_copy(update={"checklist": checklist})


def _append_persisted_page_findings(
    scope: ApprovalReadinessScopeDTO,
    report: WorkflowConsistencyReport,
    findings: list[ApprovalReadinessFindingDTO],
) -> None:
    if (
        report.project_id != scope.project_id
        or report.page_number != scope.page_number
        or scope.page_id != str(scope.page_number)
    ):
        findings.append(
            _finding(
                "PERSISTED_PAGE_BINDING_MISMATCH",
                "blocked",
                "persisted Page evidence does not match the selected Project and Page",
            )
        )
    if not report.valid or report.errors:
        findings.append(
            _finding(
                "PERSISTED_PAGE_STATE_UNVERIFIED",
                "blocked",
                "persisted Page state and workflow history are not consistent",
            )
        )
    if report.current_state == PageState.QUALITY_CHECKED:
        return
    if report.current_state == PageState.GENERATED:
        findings.append(
            _finding(
                "QUALITY_CHECK_REQUIRED",
                "needs_review",
                "Page must be persisted as QualityChecked before readiness",
            )
        )
        return
    if report.current_state == PageState.APPROVED:
        findings.append(
            _finding(
                "PAGE_ALREADY_APPROVED",
                "blocked",
                "Approved is terminal historical evidence and cannot be reassessed",
            )
        )
        return
    findings.append(
        _finding(
            "PAGE_NOT_GENERATED",
            "blocked",
            "Page has not reached the generated visual-review boundary",
        )
    )


def _append_attempt_binding_findings(
    scope: ApprovalReadinessScopeDTO,
    report: AttemptToEvidenceBindingReport,
    findings: list[ApprovalReadinessFindingDTO],
) -> None:
    if report.attempt_id != scope.attempt_id:
        findings.append(
            _finding(
                "ATTEMPT_REFERENCE_MISMATCH",
                "blocked",
                "selected attempt does not match the exact-binding report",
            )
        )
    if report.status == "blocked" or report.findings or not report.bound:
        findings.append(
            _finding(
                "GENERATION_BINDING_BLOCKED",
                "blocked",
                "generation evidence and registered output are not exactly bound",
            )
        )
    elif report.status != "ready" or not report.ready:
        findings.append(
            _finding(
                "GENERATION_BINDING_INCOMPLETE",
                "needs_review",
                "generation evidence binding is not ready",
            )
        )

    matching = tuple(
        envelope
        for envelope in report.generation_evidence_validation_report.envelopes
        if envelope.attempt_id == scope.attempt_id
    )
    if len(matching) != 1:
        findings.append(
            _finding(
                "GENERATION_EVIDENCE_AMBIGUOUS",
                "blocked",
                "exactly one generation evidence envelope must match the attempt",
            )
        )
        return
    envelope = matching[0]
    if envelope.output.output_asset_id != scope.output_asset_id:
        findings.append(
            _finding(
                "OUTPUT_ASSET_REFERENCE_MISMATCH",
                "blocked",
                "selected output asset does not match generation evidence",
            )
        )
    if envelope.provenance_reference != scope.provenance_reference:
        findings.append(
            _finding(
                "PROVENANCE_REFERENCE_MISMATCH",
                "blocked",
                "selected provenance does not match generation evidence",
            )
        )


def _append_workflow_page_binding_findings(
    scope: ApprovalReadinessScopeDTO,
    report: DurableEvidenceWorkflowBindingReport,
    findings: list[ApprovalReadinessFindingDTO],
) -> None:
    if report.status != "eligible" or not report.eligible or report.findings:
        findings.append(
            _finding(
                "WORKFLOW_PAGE_BINDING_BLOCKED",
                "blocked",
                "authoritative workflow Page and durable evidence binding is not eligible",
            )
        )
    if (
        report.project_id != scope.project_id
        or report.page_id != scope.page_id
        or report.target_page_reference != scope.target_page_reference
        or report.attempt_id != scope.attempt_id
        or report.output_asset_id != scope.output_asset_id
    ):
        findings.append(
            _finding(
                "WORKFLOW_PAGE_BINDING_MISMATCH",
                "blocked",
                "selected Project, Page, attempt, and output are not one authoritative chain",
            )
        )


def _append_visual_qa_findings(
    scope: ApprovalReadinessScopeDTO,
    report: VisualContinuityQAReport,
    attempt_binding_report: AttemptToEvidenceBindingReport,
    identity_validation_report: IdentityValidationReport | None,
    findings: list[ApprovalReadinessFindingDTO],
) -> None:
    if report.status == "blocked" or any(
        item.classification == "blocked" for item in report.findings
    ):
        findings.append(
            _finding(
                "VISUAL_QA_BLOCKED",
                "blocked",
                "advisory Visual QA contains a blocking finding",
            )
        )
    if not _visual_qa_report_is_complete(
        report,
        attempt_binding_report,
        identity_validation_report,
    ):
        findings.append(
            _finding(
                "VISUAL_QA_INCOMPLETE",
                "needs_review",
                "advisory Visual QA comparisons and checklist are required",
            )
        )
    if any(
        item.classification in {"missing_evidence", "evidence_conflict"} for item in report.findings
    ):
        findings.append(
            _finding(
                "VISUAL_QA_EVIDENCE_UNRESOLVED",
                "needs_review",
                "advisory Visual QA contains unresolved logical evidence",
            )
        )
    for comparison in report.comparisons:
        panel = comparison.current_panel
        if panel.page_id != scope.page_id:
            findings.append(
                _finding(
                    "VISUAL_QA_PAGE_MISMATCH",
                    "blocked",
                    "Visual QA current panel does not belong to the selected Page",
                )
            )
        for supplied, expected, code in (
            (panel.generation_attempt_id, scope.attempt_id, "VISUAL_QA_ATTEMPT_MISMATCH"),
            (
                panel.generation_output_asset_id,
                scope.output_asset_id,
                "VISUAL_QA_OUTPUT_ASSET_MISMATCH",
            ),
            (
                panel.generation_provenance_reference,
                scope.provenance_reference,
                "VISUAL_QA_PROVENANCE_MISMATCH",
            ),
        ):
            if supplied is None:
                findings.append(
                    _finding(
                        "VISUAL_QA_BINDING_INCOMPLETE",
                        "needs_review",
                        "Visual QA current panel must carry the exact generation references",
                    )
                )
            elif supplied != expected:
                findings.append(
                    _finding(code, "blocked", "Visual QA generation reference does not match")
                )


def _visual_qa_report_is_complete(
    report: VisualContinuityQAReport,
    attempt_binding_report: AttemptToEvidenceBindingReport,
    identity_validation_report: IdentityValidationReport | None,
) -> bool:
    if not report.comparisons or not report.checklist:
        return False
    rebuilt = VisualContinuityQAService().validate(
        report.comparisons,
        identity_validation_report=identity_validation_report,
        generation_evidence_validation_report=(
            attempt_binding_report.generation_evidence_validation_report
        ),
    )
    return report == rebuilt


def _append_human_judgment_findings(
    scope: ApprovalReadinessScopeDTO,
    judgment: HumanVisualJudgmentDTO | None,
    findings: list[ApprovalReadinessFindingDTO],
) -> None:
    if judgment is None:
        findings.append(
            _finding(
                "HUMAN_VISUAL_JUDGMENT_REQUIRED",
                "needs_review",
                "explicit human visual judgment is required",
            )
        )
        return

    for supplied, expected, code in (
        (judgment.project_id, scope.project_id, "HUMAN_PROJECT_MISMATCH"),
        (judgment.page_id, scope.page_id, "HUMAN_PAGE_MISMATCH"),
        (judgment.attempt_id, scope.attempt_id, "HUMAN_ATTEMPT_MISMATCH"),
        (judgment.output_asset_id, scope.output_asset_id, "HUMAN_OUTPUT_ASSET_MISMATCH"),
        (
            judgment.provenance_reference,
            scope.provenance_reference,
            "HUMAN_PROVENANCE_MISMATCH",
        ),
        (
            judgment.qa_report_reference,
            scope.qa_report_reference,
            "HUMAN_QA_REPORT_MISMATCH",
        ),
    ):
        if supplied != expected:
            findings.append(
                _finding(code, "blocked", "human judgment is bound to different evidence")
            )

    _append_human_checklist_findings(judgment, findings)
    _append_human_overall_finding(judgment, findings)


def _append_human_checklist_findings(
    judgment: HumanVisualJudgmentDTO,
    findings: list[ApprovalReadinessFindingDTO],
) -> None:
    counts = {criterion: 0 for criterion in _REQUIRED_CRITERIA}
    for item in judgment.checklist:
        counts[item.criterion] += 1
        if item.outcome == "blocked":
            findings.append(
                _finding(
                    "HUMAN_CHECKLIST_BLOCKED",
                    "blocked",
                    "human reviewer explicitly blocks a visual criterion",
                    criterion=item.criterion,
                )
            )
        elif item.outcome == "needs_review":
            findings.append(
                _finding(
                    "HUMAN_CHECKLIST_NEEDS_REVIEW",
                    "needs_review",
                    "human reviewer requests further visual review",
                    criterion=item.criterion,
                )
            )
        elif item.outcome == "not_applicable" and item.criterion not in _OPTIONAL_CRITERIA:
            findings.append(
                _finding(
                    "HUMAN_CHECKLIST_INVALID_NOT_APPLICABLE",
                    "needs_review",
                    "mandatory visual criterion cannot be marked not applicable",
                    criterion=item.criterion,
                )
            )
    for criterion, count in counts.items():
        if count == 0:
            findings.append(
                _finding(
                    "HUMAN_CHECKLIST_INCOMPLETE",
                    "needs_review",
                    "mandatory human visual criterion is missing",
                    criterion=criterion,
                )
            )
        elif count > 1:
            findings.append(
                _finding(
                    "HUMAN_CHECKLIST_DUPLICATE",
                    "blocked",
                    "human visual criterion is supplied more than once",
                    criterion=criterion,
                )
            )


def _append_human_overall_finding(
    judgment: HumanVisualJudgmentDTO,
    findings: list[ApprovalReadinessFindingDTO],
) -> None:
    if judgment.overall_judgment == "blocked":
        findings.append(
            _finding(
                "HUMAN_JUDGMENT_BLOCKED",
                "blocked",
                "human reviewer explicitly blocks approval consideration",
            )
        )
    elif judgment.overall_judgment == "further_review_required":
        findings.append(
            _finding(
                "HUMAN_JUDGMENT_NEEDS_REVIEW",
                "needs_review",
                "human reviewer requests further review",
            )
        )


def _finding(
    code: str,
    status: FindingStatus,
    message: str,
    *,
    criterion: str = "",
) -> ApprovalReadinessFindingDTO:
    return ApprovalReadinessFindingDTO(
        code=code,
        status=status,
        message=message,
        criterion=criterion,
    )


def _finding_key(item: ApprovalReadinessFindingDTO) -> tuple[str, str, str, str]:
    return (item.code, item.status, item.criterion, item.message)


def _readiness_status(
    findings: tuple[ApprovalReadinessFindingDTO, ...],
) -> ReadinessStatus:
    if any(item.status == "blocked" for item in findings):
        return "blocked"
    if findings:
        return "needs_review"
    return "ready"
