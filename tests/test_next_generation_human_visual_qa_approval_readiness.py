"""Focused contracts for internal human visual QA approval readiness."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from manga_director.domain.state_machine import PageState
from manga_director.production.next_generation_asset_registration import (
    OutputAssetRegistrationReport,
)
from manga_director.production.next_generation_attempt_to_evidence_binding import (
    AttemptToEvidenceBindingReport,
)
from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    DurableEvidenceWorkflowBindingReport,
)
from manga_director.production.next_generation_generation_evidence import (
    EvidenceValueDTO,
    GenerationConfigurationEvidenceDTO,
    GenerationEvidenceEnvelopeDTO,
    GenerationEvidenceValidationReport,
    GenerationInputEvidenceDTO,
    GenerationOutputEvidenceDTO,
)
from manga_director.production.next_generation_human_visual_qa_approval_readiness import (
    ApprovalReadinessScopeDTO,
    HumanVisualChecklistDecisionDTO,
    HumanVisualCriterion,
    HumanVisualJudgmentDTO,
    HumanVisualQAApprovalReadinessService,
)
from manga_director.production.next_generation_page_composition import AcceptedPanelSource
from manga_director.production.next_generation_page_generation_plan import PanelRectangle
from manga_director.production.next_generation_page_output_proof import (
    DeterministicCompositionPageOutputProof,
)
from manga_director.production.next_generation_visual_continuity_qa import (
    ContinuityComparisonDTO,
    PanelContinuityEvidenceDTO,
    VisualContinuityFindingDTO,
    VisualContinuityQAReport,
    VisualContinuityQAService,
)
from manga_director.production.reliability import WorkflowConsistencyReport

ROOT = Path(__file__).resolve().parents[1]
CRITERIA: tuple[HumanVisualCriterion, ...] = (
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


def _known(value: str | int) -> EvidenceValueDTO:
    return EvidenceValueDTO(availability="known", value=value)


def _scope() -> ApprovalReadinessScopeDTO:
    return ApprovalReadinessScopeDTO(
        project_id="project:001",
        page_id="1",
        page_number=1,
        target_page_reference="page:001",
        attempt_id="attempt:001",
        output_asset_id="asset:page-001",
        provenance_reference="provenance:001",
        qa_report_reference="qa-report:001",
    )


def _generation_report() -> GenerationEvidenceValidationReport:
    envelope = GenerationEvidenceEnvelopeDTO(
        attempt_id="attempt:001",
        observed_at=datetime(2026, 10, 17, tzinfo=UTC),
        provenance_reference="provenance:001",
        input=GenerationInputEvidenceDTO(input_reference="input:001"),
        output=GenerationOutputEvidenceDTO(
            output_asset_id="asset:page-001",
            media_type="image/png",
        ),
        configuration=GenerationConfigurationEvidenceDTO(
            provider_id=_known("provider:mock"),
            model_id=_known("model:mock"),
            model_version=_known("v1"),
            workflow_id=_known("workflow:page"),
            workflow_version=_known("v1"),
            seed=_known(1),
        ),
    )
    return GenerationEvidenceValidationReport(
        envelopes=(envelope,),
        status="ready",
        ready=True,
    )


def _binding_report(
    *,
    status: str = "ready",
    bound: bool = True,
    ready: bool = True,
    attempt_id: str = "attempt:001",
    generation_report: GenerationEvidenceValidationReport | None = None,
) -> AttemptToEvidenceBindingReport:
    return AttemptToEvidenceBindingReport.model_construct(
        generation_evidence_validation_report=generation_report or _generation_report(),
        output_asset_registration_report=cast(OutputAssetRegistrationReport, object()),
        attempt_id=attempt_id,
        request_id="request:001",
        findings=(),
        status=status,
        bound=bound,
        ready=ready,
        analysis_only=True,
    )


def _workflow_binding_report(
    *,
    project_id: str = "project:001",
    page_id: str = "1",
    status: str = "eligible",
    eligible: bool = True,
) -> DurableEvidenceWorkflowBindingReport:
    return DurableEvidenceWorkflowBindingReport(
        attempt_id="attempt:001",
        provider_reference="provider:mock",
        output_asset_id="asset:page-001",
        project_id=project_id,
        page_id=page_id,
        target_page_reference="page:001",
        status=status,
        eligible=eligible,
    )


def _consistency_report(
    *,
    state: PageState = PageState.QUALITY_CHECKED,
    project_id: str = "project:001",
    page_number: int = 1,
    valid: bool = True,
) -> WorkflowConsistencyReport:
    return WorkflowConsistencyReport(
        project_id=project_id,
        page_number=page_number,
        valid=valid,
        current_state=state,
        errors=[] if valid else ["Persisted history mismatch."],
    )


def _visual_report(*, page_id: str = "1") -> VisualContinuityQAReport:
    previous = PanelContinuityEvidenceDTO(
        page_id="0",
        panel_id="panel:previous",
        generation_attempt_id="attempt:001",
        generation_output_asset_id="asset:page-001",
        generation_provenance_reference="provenance:001",
        characters=(),
        prop_ids=(),
        location=_known("location:studio"),
        time=_known("time:day"),
    )
    comparison = ContinuityComparisonDTO(
        comparison_id="comparison:001",
        current_panel=PanelContinuityEvidenceDTO(
            page_id=page_id,
            panel_id="panel:001",
            generation_attempt_id="attempt:001",
            generation_output_asset_id="asset:page-001",
            generation_provenance_reference="provenance:001",
            characters=(),
            prop_ids=(),
            location=_known("location:studio"),
            time=_known("time:day"),
        ),
        previous_panel=previous,
    )
    return VisualContinuityQAService().validate(
        (comparison,),
        generation_evidence_validation_report=_generation_report(),
    )


def _human_checklist(
    *,
    override_criterion: HumanVisualCriterion | None = None,
    override_outcome: str = "acceptable",
) -> tuple[HumanVisualChecklistDecisionDTO, ...]:
    return tuple(
        HumanVisualChecklistDecisionDTO(
            criterion=criterion,
            outcome=override_outcome if criterion == override_criterion else "acceptable",
            rationale=f"{criterion.replace('_', ' ')} inspected",
        )
        for criterion in CRITERIA
    )


def _judgment(
    *,
    checklist: tuple[HumanVisualChecklistDecisionDTO, ...] | None = None,
    overall_judgment: str = "acceptable_for_approval_consideration",
    **overrides: object,
) -> HumanVisualJudgmentDTO:
    values: dict[str, object] = {
        "review_id": "review:001",
        "project_id": "project:001",
        "page_id": "1",
        "attempt_id": "attempt:001",
        "output_asset_id": "asset:page-001",
        "provenance_reference": "provenance:001",
        "qa_report_reference": "qa-report:001",
        "reviewer_id": "reviewer:001",
        "reviewed_at": datetime(2026, 10, 17, tzinfo=UTC),
        "checklist": checklist if checklist is not None else _human_checklist(),
        "overall_judgment": overall_judgment,
        "rationale": "Exact output inspected and acceptable",
    }
    values.update(overrides)
    return HumanVisualJudgmentDTO(**values)


def _assess(
    *,
    scope: ApprovalReadinessScopeDTO | None = None,
    binding: AttemptToEvidenceBindingReport | None = None,
    workflow_binding: DurableEvidenceWorkflowBindingReport | None = None,
    consistency: WorkflowConsistencyReport | None = None,
    visual: VisualContinuityQAReport | None = None,
    judgment: HumanVisualJudgmentDTO | None = None,
):
    return HumanVisualQAApprovalReadinessService().assess(
        scope or _scope(),
        binding or _binding_report(),
        workflow_binding or _workflow_binding_report(),
        consistency or _consistency_report(),
        visual or _visual_report(),
        identity_validation_report=None,
        human_judgment=_judgment() if judgment is None else judgment,
    )


def test_complete_quality_checked_evidence_is_advisory_ready() -> None:
    report = _assess()

    assert report.status == "ready"
    assert report.ready is True
    assert report.findings == ()
    assert report.missing_prerequisites == ()
    assert report.persisted_page_state == PageState.QUALITY_CHECKED
    assert report.analysis_only is True
    for forbidden in (
        "approved",
        "approved_by",
        "command",
        "next_state",
        "provider_choice",
        "regenerate",
        "retry",
    ):
        assert forbidden not in type(report).model_fields


def test_generated_page_needs_quality_check_without_transition() -> None:
    report = _assess(consistency=_consistency_report(state=PageState.GENERATED))

    assert report.status == "needs_review"
    assert report.ready is False
    assert "QUALITY_CHECK_REQUIRED" in {item.code for item in report.findings}
    assert report.persisted_page_state == PageState.GENERATED


@pytest.mark.parametrize("page_state", (PageState.DRAFT, PageState.PROMPT_BUILT))
def test_pre_generation_page_is_blocked(page_state: PageState) -> None:
    report = _assess(consistency=_consistency_report(state=page_state))

    assert report.status == "blocked"
    assert "PAGE_NOT_GENERATED" in {item.code for item in report.findings}


def test_already_approved_page_is_historical_only() -> None:
    report = _assess(consistency=_consistency_report(state=PageState.APPROVED))

    assert report.status == "blocked"
    assert "PAGE_ALREADY_APPROVED" in {item.code for item in report.findings}


@pytest.mark.parametrize(
    ("status", "bound", "ready", "expected_code", "expected_status"),
    (
        ("blocked", False, False, "GENERATION_BINDING_BLOCKED", "blocked"),
        ("needs_evidence", True, False, "GENERATION_BINDING_INCOMPLETE", "needs_review"),
        ("needs_review", True, False, "GENERATION_BINDING_INCOMPLETE", "needs_review"),
    ),
)
def test_generation_binding_is_fail_closed(
    status: str,
    bound: bool,
    ready: bool,
    expected_code: str,
    expected_status: str,
) -> None:
    report = _assess(binding=_binding_report(status=status, bound=bound, ready=ready))

    assert report.status == expected_status
    assert expected_code in {item.code for item in report.findings}


@pytest.mark.parametrize(
    ("field", "value", "expected_code"),
    (
        ("project_id", "project:other", "HUMAN_PROJECT_MISMATCH"),
        ("page_id", "page:other", "HUMAN_PAGE_MISMATCH"),
        ("attempt_id", "attempt:other", "HUMAN_ATTEMPT_MISMATCH"),
        ("output_asset_id", "asset:other", "HUMAN_OUTPUT_ASSET_MISMATCH"),
        ("provenance_reference", "provenance:other", "HUMAN_PROVENANCE_MISMATCH"),
        ("qa_report_reference", "qa-report:other", "HUMAN_QA_REPORT_MISMATCH"),
    ),
)
def test_human_judgment_must_match_exact_scope(field: str, value: str, expected_code: str) -> None:
    report = _assess(judgment=_judgment(**{field: value}))

    assert report.status == "blocked"
    assert expected_code in {item.code for item in report.findings}


def test_generation_asset_and_provenance_mismatch_are_blocked() -> None:
    envelope = (
        _generation_report()
        .envelopes[0]
        .model_copy(
            update={
                "output": GenerationOutputEvidenceDTO(output_asset_id="asset:other"),
                "provenance_reference": "provenance:other",
            }
        )
    )
    generation = _generation_report().model_copy(update={"envelopes": (envelope,)})
    report = _assess(binding=_binding_report(generation_report=generation))

    assert report.status == "blocked"
    assert {
        "OUTPUT_ASSET_REFERENCE_MISMATCH",
        "PROVENANCE_REFERENCE_MISMATCH",
    } <= {item.code for item in report.findings}


def test_visual_qa_blocker_and_page_mismatch_are_blocked() -> None:
    finding = VisualContinuityFindingDTO(
        code="CONFLICT",
        classification="blocked",
        severity="blocked",
        message="Conflicting supplied evidence.",
    )
    visual = _visual_report(page_id="page:other").model_copy(
        update={"findings": (finding,), "status": "blocked"}
    )
    report = _assess(visual=visual)

    assert report.status == "blocked"
    assert {"VISUAL_QA_BLOCKED", "VISUAL_QA_PAGE_MISMATCH"} <= {
        item.code for item in report.findings
    }


def test_missing_visual_qa_and_human_judgment_need_review() -> None:
    visual = VisualContinuityQAReport(status="needs_human_review")
    report = HumanVisualQAApprovalReadinessService().assess(
        _scope(),
        _binding_report(),
        _workflow_binding_report(),
        _consistency_report(),
        visual,
        identity_validation_report=None,
        human_judgment=None,
    )

    assert report.status == "needs_review"
    assert {
        "VISUAL_QA_INCOMPLETE",
        "HUMAN_VISUAL_JUDGMENT_REQUIRED",
    } <= {item.code for item in report.findings}


def test_incomplete_hand_built_visual_qa_cannot_be_ready() -> None:
    complete = _visual_report()
    incomplete = complete.model_copy(update={"checklist": complete.checklist[:1]})

    report = _assess(visual=incomplete)

    assert report.status == "needs_review"
    assert "VISUAL_QA_INCOMPLETE" in {item.code for item in report.findings}


def test_visual_qa_with_removed_non_review_finding_cannot_be_ready() -> None:
    comparison = _visual_report().comparisons[0]
    previous_panel = comparison.previous_panel
    assert previous_panel is not None
    previous = previous_panel.model_copy(update={"prop_ids": ("prop:previous",)})
    current = comparison.current_panel.model_copy(update={"prop_ids": ("prop:current",)})
    conflicted = VisualContinuityQAService().validate(
        (comparison.model_copy(update={"previous_panel": previous, "current_panel": current}),),
        generation_evidence_validation_report=_generation_report(),
    )
    tampered = conflicted.model_copy(
        update={
            "findings": tuple(
                item for item in conflicted.findings if item.classification != "evidence_conflict"
            )
        }
    )

    report = _assess(visual=tampered)

    assert report.status == "needs_review"
    assert "VISUAL_QA_INCOMPLETE" in {item.code for item in report.findings}


def test_cross_project_or_unverified_persisted_page_is_blocked() -> None:
    cross_project = _assess(workflow_binding=_workflow_binding_report(project_id="project:other"))
    unverified = _assess(consistency=_consistency_report(valid=False))

    assert cross_project.status == "blocked"
    assert "WORKFLOW_PAGE_BINDING_MISMATCH" in {item.code for item in cross_project.findings}
    assert unverified.status == "blocked"
    assert "PERSISTED_PAGE_STATE_UNVERIFIED" in {item.code for item in unverified.findings}


@pytest.mark.parametrize(
    ("outcome", "overall", "expected_status", "expected_code"),
    (
        (
            "needs_review",
            "acceptable_for_approval_consideration",
            "needs_review",
            "HUMAN_CHECKLIST_NEEDS_REVIEW",
        ),
        ("blocked", "acceptable_for_approval_consideration", "blocked", "HUMAN_CHECKLIST_BLOCKED"),
        ("acceptable", "further_review_required", "needs_review", "HUMAN_JUDGMENT_NEEDS_REVIEW"),
        ("acceptable", "blocked", "blocked", "HUMAN_JUDGMENT_BLOCKED"),
    ),
)
def test_explicit_human_outcomes_control_readiness(
    outcome: str,
    overall: str,
    expected_status: str,
    expected_code: str,
) -> None:
    checklist = _human_checklist(override_criterion="composition", override_outcome=outcome)
    report = _assess(judgment=_judgment(checklist=checklist, overall_judgment=overall))

    assert report.status == expected_status
    assert expected_code in {item.code for item in report.findings}


def test_incomplete_duplicate_and_invalid_not_applicable_checklist_fail_closed() -> None:
    incomplete = _human_checklist()[:-1]
    incomplete_report = _assess(judgment=_judgment(checklist=incomplete))
    duplicate_report = _assess(
        judgment=_judgment(checklist=_human_checklist() + (_human_checklist()[0],))
    )
    invalid_na = _assess(
        judgment=_judgment(
            checklist=_human_checklist(
                override_criterion="character_identity", override_outcome="not_applicable"
            )
        )
    )

    assert incomplete_report.status == "needs_review"
    assert "HUMAN_CHECKLIST_INCOMPLETE" in {item.code for item in incomplete_report.findings}
    assert duplicate_report.status == "blocked"
    assert "HUMAN_CHECKLIST_DUPLICATE" in {item.code for item in duplicate_report.findings}
    assert invalid_na.status == "needs_review"
    assert "HUMAN_CHECKLIST_INVALID_NOT_APPLICABLE" in {item.code for item in invalid_na.findings}


def test_canonical_ordering_is_deterministic_and_preserves_inputs() -> None:
    judgment = _judgment(checklist=tuple(reversed(_human_checklist())))
    before = judgment.model_dump(mode="json")

    first = _assess(judgment=judgment)
    second = _assess(judgment=judgment)

    assert first == second
    assert judgment.model_dump(mode="json") == before
    assert tuple(item.criterion for item in first.human_judgment.checklist) == tuple(
        sorted(CRITERIA)
    )


def test_models_are_frozen_closed_and_reject_unsafe_review_data() -> None:
    scope = _scope()
    with pytest.raises(ValidationError):
        scope.page_number = 2
    with pytest.raises(ValidationError):
        ApprovalReadinessScopeDTO(**(_scope().model_dump() | {"extra": "forbidden"}))
    with pytest.raises(ValidationError, match="timezone-aware"):
        _judgment(reviewed_at=datetime(2026, 10, 17))
    with pytest.raises(ValidationError):
        _judgment(reviewer_id="reviewer@example.com")
    with pytest.raises(ValidationError):
        _judgment(rationale="See https://example.invalid/review")
    with pytest.raises(ValidationError):
        _judgment(policy_reference="policy:api_key:private")
    with pytest.raises(ValidationError):
        _judgment(prior_review_reference="")
    with pytest.raises(ValidationError, match="200 characters"):
        _judgment(reviewer_id="r" * 201)


def test_exact_composition_proof_preserves_readiness_without_provider_identity() -> None:
    scope = ApprovalReadinessScopeDTO(
        project_id="project-1",
        page_id="1",
        page_number=1,
        target_page_reference="page.project-1.1",
        attempt_id="composition-1",
        output_asset_id="composite-1",
        provenance_reference="composition-provenance-1",
        qa_report_reference="qa-report-1",
    )
    source = AcceptedPanelSource(
        plan_id="plan-1",
        plan_fingerprint="a" * 64,
        project_id="project-1",
        page_id="1",
        panel_id="panel-1",
        panel_order=1,
        request_id="request-1",
        request_fingerprint="b" * 64,
        attempt_id="panel-attempt-1",
        evidence_id="panel-evidence-1",
        asset_id="panel-asset-1",
        content_sha256="c" * 64,
        width=1,
        height=1,
        rectangle=PanelRectangle(
            left=46875, top=31250, right=953125, bottom=968750
        ),
    )
    proof = DeterministicCompositionPageOutputProof(
        project_id=scope.project_id,
        page_id=scope.page_id,
        target_page_reference=scope.target_page_reference,
        attempt_id=scope.attempt_id,
        provenance_reference=scope.provenance_reference,
        asset_id=scope.output_asset_id,
        content_sha256="d" * 64,
        plan_id="plan-1",
        plan_fingerprint="a" * 64,
        request_fingerprint="e" * 64,
        evidence_id="composition-evidence-1",
        evidence_sha256="f" * 64,
        ordered_sources=(source,),
    )
    comparison = ContinuityComparisonDTO(
        comparison_id="comparison-1",
        current_panel=PanelContinuityEvidenceDTO(
            page_id=scope.page_id,
            panel_id="panel-1",
            generation_attempt_id=scope.attempt_id,
            generation_output_asset_id=scope.output_asset_id,
            generation_provenance_reference=scope.provenance_reference,
            characters=(),
            prop_ids=(),
            location=_known("location-studio"),
            time=_known("time-day"),
        ),
    )
    visual = VisualContinuityQAService().validate((comparison,))
    judgment = HumanVisualJudgmentDTO(
        review_id="review-1",
        project_id=scope.project_id,
        page_id=scope.page_id,
        attempt_id=scope.attempt_id,
        output_asset_id=scope.output_asset_id,
        provenance_reference=scope.provenance_reference,
        qa_report_reference=scope.qa_report_reference,
        reviewer_id="reviewer-1",
        reviewed_at=datetime(2026, 10, 24, tzinfo=UTC),
        checklist=_human_checklist(),
        overall_judgment="acceptable_for_approval_consideration",
        rationale="Exact composite and complete ordered source manifest inspected",
    )

    report = HumanVisualQAApprovalReadinessService()._assess_composition_proof(
        scope,
        proof,
        _consistency_report(project_id="project-1"),
        visual,
        human_judgment=judgment,
    )

    assert report.findings == ()
    assert report.status == "ready"
    assert report.ready


def test_source_has_no_public_export_io_provider_workflow_or_clock_boundary() -> None:
    source = (
        ROOT / "src/manga_director/production/next_generation_human_visual_qa_approval_readiness.py"
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
    assert "next_generation_human_visual_qa_approval_readiness" not in production_init
