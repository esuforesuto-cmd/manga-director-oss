"""Focused contracts for internal Human Review Decision validation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.production.next_generation_human_review_decision import (
    HumanReviewDecisionRecordDTO,
    HumanReviewDecisionValidationService,
)

ROOT = Path(__file__).resolve().parents[1]


def _record(
    *,
    decision_id: str = "decision:001",
    reviewer_id: str = "reviewer:editor-01",
    reviewed_at: datetime | None = None,
    qa_report_reference: str = "qa-report:001",
    target_type: str = "finding",
    target_reference: str = "finding:costume:001",
    decision: str = "accepted",
    rationale_reference: str | None = None,
) -> HumanReviewDecisionRecordDTO:
    return HumanReviewDecisionRecordDTO(
        decision_id=decision_id,
        reviewer_id=reviewer_id,
        reviewed_at=reviewed_at or datetime(2026, 8, 21, 0, 0, tzinfo=UTC),
        qa_report_reference=qa_report_reference,
        target_type=target_type,
        target_reference=target_reference,
        decision=decision,
        rationale_reference=rationale_reference,
    )


def test_dtos_are_frozen_closed_and_have_no_execution_fields() -> None:
    record = _record()

    with pytest.raises(ValidationError):
        record.decision = "unresolved"
    with pytest.raises(ValidationError):
        HumanReviewDecisionRecordDTO(
            decision_id="decision:001",
            reviewer_id="reviewer:editor-01",
            reviewed_at="2026-08-21T00:00:00Z",
            qa_report_reference="qa-report:001",
            target_type="finding",
            target_reference="finding:costume:001",
            decision="accepted",
            raw_rationale="private text",
        )

    report = HumanReviewDecisionValidationService().validate((_record(),))
    for forbidden in (
        "approved",
        "rejected",
        "regenerate",
        "retry",
        "workflow_transition",
        "provider_choice",
        "latest_decision",
    ):
        assert forbidden not in type(report).model_fields
    assert report.analysis_only is True


def test_canonical_ordering_is_deterministic_and_preserves_input() -> None:
    later = _record(decision_id="decision:002", target_reference="finding:002")
    earlier = _record(decision_id="decision:001", target_reference="finding:001")
    supplied = (later, earlier)
    before = tuple(item.model_dump(mode="json") for item in supplied)

    first = HumanReviewDecisionValidationService().validate(supplied)
    second = HumanReviewDecisionValidationService().validate(supplied)

    assert tuple(item.decision_id for item in first.decisions) == ("decision:001", "decision:002")
    assert first == second
    assert tuple(item.model_dump(mode="json") for item in supplied) == before


def test_naive_timestamp_and_invalid_vocabularies_are_rejected() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        _record(reviewed_at=datetime(2026, 8, 21, 0, 0))
    with pytest.raises(ValidationError):
        _record(decision="rejected")
    with pytest.raises(ValidationError):
        _record(target_type="panel")


@pytest.mark.parametrize("decision", ("accepted", "change_requested", "unresolved", "not_applicable"))
@pytest.mark.parametrize("target_type", ("report", "comparison", "finding", "checklist"))
def test_decision_vocabulary_and_target_types_are_closed(
    decision: str, target_type: str
) -> None:
    target_reference = "qa-report:001" if target_type == "report" else f"{target_type}:001"
    record = _record(decision=decision, target_type=target_type, target_reference=target_reference)

    report = HumanReviewDecisionValidationService().validate((record,))

    assert report.decisions[0].decision == decision
    assert report.decisions[0].target_type == target_type


def test_duplicate_decision_id_is_blocked() -> None:
    report = HumanReviewDecisionValidationService().validate(
        (_record(), _record(reviewer_id="reviewer:editor-02"))
    )

    assert "DUPLICATE_DECISION_ID" in {item.code for item in report.findings}
    assert report.status == "blocked"


def test_duplicate_reviewer_target_is_blocked() -> None:
    report = HumanReviewDecisionValidationService().validate(
        (
            _record(decision_id="decision:001"),
            _record(decision_id="decision:002"),
        )
    )

    assert "DUPLICATE_REVIEWER_TARGET_DECISION" in {item.code for item in report.findings}
    assert report.status == "blocked"


def test_invalid_report_target_binding_is_blocked() -> None:
    report = HumanReviewDecisionValidationService().validate(
        (_record(target_type="report", target_reference="qa-report:other"),)
    )

    assert "INVALID_REPORT_TARGET_BINDING" in {item.code for item in report.findings}
    assert report.status == "blocked"


def test_conflicting_human_decisions_need_review_without_selection() -> None:
    report = HumanReviewDecisionValidationService().validate(
        (
            _record(decision_id="decision:001", decision="accepted"),
            _record(
                decision_id="decision:002",
                reviewer_id="reviewer:editor-02",
                decision="change_requested",
            ),
        )
    )

    assert "CONFLICTING_HUMAN_DECISIONS" in {item.code for item in report.findings}
    assert report.status == "needs_review"
    assert "selected_decision" not in type(report).model_fields
    assert "latest_decision" not in type(report).model_fields


def test_unresolved_is_valid_and_returns_a_review_notice() -> None:
    report = HumanReviewDecisionValidationService().validate((_record(decision="unresolved"),))

    assert tuple((item.code, item.status) for item in report.findings) == (
        ("UNRESOLVED_HUMAN_DECISION", "needs_review"),
    )
    assert report.status == "needs_review"
    assert report.ready is False


def test_partial_review_is_not_inferred() -> None:
    report = HumanReviewDecisionValidationService().validate((_record(),))

    assert report.status == "ready"
    assert not report.findings
    assert "partial" not in type(report).model_fields


def test_rationale_reference_is_optional_and_raw_sensitive_values_are_rejected() -> None:
    assert _record(rationale_reference="audit:decision-note:001").rationale_reference == (
        "audit:decision-note:001"
    )
    for field_name, value in (
        ("reviewer_id", "reviewer@example.com"),
        ("qa_report_reference", "https://example.invalid/report"),
        ("target_reference", "C:\\private\\report"),
        ("rationale_reference", "note:api_key:secret"),
    ):
        values = _record().model_dump()
        values[field_name] = value
        with pytest.raises(ValidationError):
            HumanReviewDecisionRecordDTO(**values)


def test_source_keeps_public_io_provider_and_workflow_boundaries_out() -> None:
    source = (
        ROOT / "src/manga_director/production/next_generation_human_review_decision.py"
    ).read_text(encoding="utf-8")

    for forbidden in (
        "manga_director.api",
        "manga_director.cli",
        "manga_director.mcp",
        "manga_director.workflow",
        "manga_director.providers",
        ".execute(",
        ".advance(",
        "open(",
        "read_text(",
        "requests.",
        "httpx.",
        "hashlib",
        "datetime.now",
    ):
        assert forbidden not in source
    production_init = (ROOT / "src/manga_director/production/__init__.py").read_text(
        encoding="utf-8"
    )
    assert "next_generation_human_review_decision" not in production_init
