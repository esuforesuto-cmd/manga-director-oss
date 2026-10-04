"""Internal read-only validation for caller-supplied human QA decisions.

This preview contract records no decision itself.  It validates supplied human
decision evidence without approval, recovery, persistence, or workflow access.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, field_validator

from manga_director.production.director import DirectorModel

DecisionValue = Literal["accepted", "change_requested", "unresolved", "not_applicable"]
TargetType = Literal["report", "comparison", "finding", "checklist"]
FindingStatus = Literal["blocked", "needs_review"]
ReportStatus = Literal["ready", "needs_review", "blocked"]

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


class _HumanReviewDecisionModel(DirectorModel):
    """Private base for closed, immutable internal-preview DTOs."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class HumanReviewDecisionRecordDTO(_HumanReviewDecisionModel):
    """One caller-supplied human judgment about one logical QA target."""

    decision_id: str
    reviewer_id: str
    reviewed_at: datetime
    qa_report_reference: str
    target_type: TargetType
    target_reference: str
    decision: DecisionValue
    rationale_reference: str | None = None

    @field_validator("decision_id", "qa_report_reference", "target_reference", "rationale_reference")
    @classmethod
    def _validate_logical_reference(cls, value: str | None) -> str | None:
        return _logical_reference(value, "decision reference") if value is not None else None

    @field_validator("reviewer_id")
    @classmethod
    def _validate_reviewer_id(cls, value: str) -> str:
        return _logical_reference(value, "reviewer_id")

    @field_validator("reviewed_at")
    @classmethod
    def _require_timezone_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("reviewed_at must be timezone-aware")
        return value


class HumanReviewDecisionFindingDTO(_HumanReviewDecisionModel):
    """One deterministic validation finding without private decision payloads."""

    code: str
    status: FindingStatus
    message: str
    decision_id: str = ""
    reviewer_id: str = ""
    qa_report_reference: str = ""
    target_type: str = ""
    target_reference: str = ""


class HumanReviewDecisionValidationReport(_HumanReviewDecisionModel):
    """Canonical decision-evidence validation report with no execution semantics."""

    decisions: tuple[HumanReviewDecisionRecordDTO, ...] = ()
    findings: tuple[HumanReviewDecisionFindingDTO, ...] = ()
    status: ReportStatus
    ready: bool
    analysis_only: Literal[True] = True


class HumanReviewDecisionValidationService:
    """Validate supplied human decision evidence without selecting an outcome."""

    def validate(
        self, decisions: Sequence[HumanReviewDecisionRecordDTO] = ()
    ) -> HumanReviewDecisionValidationReport:
        """Return deterministic findings for caller-supplied decision records."""

        canonical_decisions = _canonical_decisions(decisions)
        findings = _decision_findings(canonical_decisions)
        ordered_findings = tuple(sorted(findings, key=_finding_key))
        status = _report_status(ordered_findings)
        return HumanReviewDecisionValidationReport(
            decisions=canonical_decisions,
            findings=ordered_findings,
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
    return value


def _canonical_decisions(
    decisions: Sequence[HumanReviewDecisionRecordDTO],
) -> tuple[HumanReviewDecisionRecordDTO, ...]:
    return tuple(
        sorted(
            decisions,
            key=lambda item: (
                item.qa_report_reference,
                item.target_type,
                item.target_reference,
                item.reviewer_id,
                item.reviewed_at.isoformat(),
                item.decision,
                item.decision_id,
                item.rationale_reference or "",
            ),
        )
    )


def _decision_findings(
    decisions: tuple[HumanReviewDecisionRecordDTO, ...],
) -> list[HumanReviewDecisionFindingDTO]:
    findings: list[HumanReviewDecisionFindingDTO] = []
    _append_duplicate_decision_id_findings(decisions, findings)
    _append_duplicate_reviewer_target_findings(decisions, findings)
    _append_invalid_report_target_findings(decisions, findings)
    _append_conflicting_decision_findings(decisions, findings)
    _append_unresolved_decision_findings(decisions, findings)
    return findings


def _append_duplicate_decision_id_findings(
    decisions: tuple[HumanReviewDecisionRecordDTO, ...],
    findings: list[HumanReviewDecisionFindingDTO],
) -> None:
    for decision_id in _duplicate_strings(item.decision_id for item in decisions):
        findings.append(
            _finding(
                "DUPLICATE_DECISION_ID",
                "blocked",
                "decision_id is supplied more than once",
                decision_id=decision_id,
            )
        )


def _append_duplicate_reviewer_target_findings(
    decisions: tuple[HumanReviewDecisionRecordDTO, ...],
    findings: list[HumanReviewDecisionFindingDTO],
) -> None:
    groups = _group_by_reviewer_target(decisions)
    for key in sorted(groups):
        matching = groups[key]
        if len(matching) > 1:
            findings.append(
                _finding(
                    "DUPLICATE_REVIEWER_TARGET_DECISION",
                    "blocked",
                    "reviewer supplies more than one decision for one QA target",
                    decision_id=matching[0].decision_id,
                    reviewer_id=matching[0].reviewer_id,
                    qa_report_reference=matching[0].qa_report_reference,
                    target_type=matching[0].target_type,
                    target_reference=matching[0].target_reference,
                )
            )


def _append_invalid_report_target_findings(
    decisions: tuple[HumanReviewDecisionRecordDTO, ...],
    findings: list[HumanReviewDecisionFindingDTO],
) -> None:
    for decision in decisions:
        if decision.target_type == "report" and decision.target_reference != decision.qa_report_reference:
            findings.append(
                _finding(
                    "INVALID_REPORT_TARGET_BINDING",
                    "blocked",
                    "report target must reference the reviewed QA report",
                    **_finding_references(decision),
                )
            )


def _append_conflicting_decision_findings(
    decisions: tuple[HumanReviewDecisionRecordDTO, ...],
    findings: list[HumanReviewDecisionFindingDTO],
) -> None:
    groups = _group_by_target(decisions)
    for key in sorted(groups):
        matching = groups[key]
        if len({item.decision for item in matching}) > 1:
            findings.append(
                _finding(
                    "CONFLICTING_HUMAN_DECISIONS",
                    "needs_review",
                    "multiple human decisions are supplied for one QA target",
                    **_finding_references(matching[0]),
                )
            )


def _append_unresolved_decision_findings(
    decisions: tuple[HumanReviewDecisionRecordDTO, ...],
    findings: list[HumanReviewDecisionFindingDTO],
) -> None:
    for decision in decisions:
        if decision.decision == "unresolved":
            findings.append(
                _finding(
                    "UNRESOLVED_HUMAN_DECISION",
                    "needs_review",
                    "human reviewer explicitly marks this QA target unresolved",
                    **_finding_references(decision),
                )
            )


def _group_by_reviewer_target(
    decisions: Iterable[HumanReviewDecisionRecordDTO],
) -> dict[tuple[str, str, str, str], list[HumanReviewDecisionRecordDTO]]:
    groups: dict[tuple[str, str, str, str], list[HumanReviewDecisionRecordDTO]] = {}
    for decision in decisions:
        groups.setdefault(
            (
                decision.qa_report_reference,
                decision.target_type,
                decision.target_reference,
                decision.reviewer_id,
            ),
            [],
        ).append(decision)
    return groups


def _group_by_target(
    decisions: Iterable[HumanReviewDecisionRecordDTO],
) -> dict[tuple[str, str, str], list[HumanReviewDecisionRecordDTO]]:
    groups: dict[tuple[str, str, str], list[HumanReviewDecisionRecordDTO]] = {}
    for decision in decisions:
        groups.setdefault(
            (decision.qa_report_reference, decision.target_type, decision.target_reference),
            [],
        ).append(decision)
    return groups


def _finding_references(decision: HumanReviewDecisionRecordDTO) -> dict[str, str]:
    return {
        "decision_id": decision.decision_id,
        "reviewer_id": decision.reviewer_id,
        "qa_report_reference": decision.qa_report_reference,
        "target_type": decision.target_type,
        "target_reference": decision.target_reference,
    }


def _finding(
    code: str,
    status: FindingStatus,
    message: str,
    *,
    decision_id: str = "",
    reviewer_id: str = "",
    qa_report_reference: str = "",
    target_type: str = "",
    target_reference: str = "",
) -> HumanReviewDecisionFindingDTO:
    return HumanReviewDecisionFindingDTO(
        code=code,
        status=status,
        message=message,
        decision_id=decision_id,
        reviewer_id=reviewer_id,
        qa_report_reference=qa_report_reference,
        target_type=target_type,
        target_reference=target_reference,
    )


def _duplicate_strings(values: Iterable[str]) -> tuple[str, ...]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return tuple(sorted(value for value, count in counts.items() if count > 1))


def _finding_key(item: HumanReviewDecisionFindingDTO) -> tuple[str, ...]:
    return (
        item.code,
        item.status,
        item.qa_report_reference,
        item.target_type,
        item.target_reference,
        item.reviewer_id,
        item.decision_id,
        item.message,
    )


def _report_status(findings: tuple[HumanReviewDecisionFindingDTO, ...]) -> ReportStatus:
    if any(item.status == "blocked" for item in findings):
        return "blocked"
    if findings:
        return "needs_review"
    return "ready"
