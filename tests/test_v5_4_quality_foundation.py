"""Contracts for the non-operational v5.4 Creative Quality Framework."""

from __future__ import annotations

from manga_director.platform import (
    QualityEngineFoundation,
    QualityEngineRequestDTO,
    QualityMetricsFoundation,
    QualityPolicyDTO,
    QualityScopeDTO,
    ReleaseCriteriaFoundation,
    ReleaseCriterionDTO,
    ReviewEvidenceDTO,
    ReviewPipelineFoundation,
    UnifiedSDKFoundation,
    ValidationEngineFoundation,
    ValidationEvidenceDTO,
)


def _scope() -> QualityScopeDTO:
    return QualityScopeDTO(
        project_id="project-001",
        page_reference="page-001",
        storyboard_persisted=True,
    )


def _policy() -> QualityPolicyDTO:
    return QualityPolicyDTO(
        policy_id="quality-default",
        revision="1",
        owner="quality-team",
        required_checks=("review", "compatibility"),
    )


def _review() -> ReviewEvidenceDTO:
    return ReviewEvidenceDTO(
        review_id="review-001",
        page_reference="page-001",
        reviewer="editor",
        completed=True,
        evidence_reference="reviews/review-001",
    )


def _validation() -> ValidationEvidenceDTO:
    return ValidationEvidenceDTO(
        validation_id="compatibility-001",
        category="compatibility",
        passed=True,
        evidence_reference="tests/compatibility-001",
    )


def _criteria() -> tuple[ReleaseCriterionDTO, ...]:
    return (
        ReleaseCriterionDTO(
            criterion_id="compatibility",
            category="compatibility",
            satisfied=True,
            evidence_reference="tests/compatibility-001",
        ),
        ReleaseCriterionDTO(
            criterion_id="approval",
            category="approval",
            satisfied=True,
            evidence_reference="approvals/release-owner",
        ),
    )


def test_review_pipeline_requires_storyboard_and_completed_quality_review() -> None:
    report = ReviewPipelineFoundation().evaluate(
        _scope().model_copy(update={"storyboard_persisted": False})
    )
    assert report.status == "blocked"
    assert report.eligible_for_human_page_approval is False
    assert report.approval_performed is False
    assert report.state_machine_authoritative is True


def test_review_pipeline_accepts_matching_completed_evidence_without_approval() -> None:
    report = ReviewPipelineFoundation().evaluate(_scope(), (_review(),))
    assert report.status == "ready"
    assert report.eligible_for_human_page_approval is True
    assert report.approval_performed is False


def test_validation_engine_is_evidence_only_and_never_controls_ci_cd() -> None:
    report = ValidationEngineFoundation().evaluate((_validation(),))
    assert report.status == "ready"
    assert report.execution_performed is False
    assert report.ci_cd_controlled is False
    failed = ValidationEngineFoundation().evaluate((_validation().model_copy(update={"passed": False}),))
    assert failed.status == "blocked"


def test_quality_metrics_expose_denominator_and_unknown_empty_input() -> None:
    report = QualityMetricsFoundation().summarize((_validation(),))
    assert report.metrics[0].value == 1.0
    assert report.metrics[0].denominator == 1
    assert QualityMetricsFoundation().summarize().status == "unknown"


def test_release_criteria_are_human_gated_and_non_publishing() -> None:
    report = ReleaseCriteriaFoundation().evaluate(_policy(), _criteria())
    assert report.status == "ready"
    assert report.eligible_for_human_release_decision is True
    assert report.release_performed is False


def test_release_criteria_block_when_required_human_sign_off_evidence_is_absent() -> None:
    report = ReleaseCriteriaFoundation().evaluate(
        _policy(),
        (
            ReleaseCriterionDTO(
                criterion_id="compatibility",
                category="compatibility",
                satisfied=True,
                evidence_reference="tests/compatibility-001",
            ),
        ),
    )
    assert report.status == "blocked"
    assert report.eligible_for_human_release_decision is False


def test_quality_engine_and_sdk_are_non_executing_and_state_machine_preserving() -> None:
    request = QualityEngineRequestDTO(
        scope=_scope(),
        policy=_policy(),
        reviews=(_review(),),
        validations=(_validation(),),
        release_criteria=_criteria(),
    )
    report = UnifiedSDKFoundation(quality=QualityEngineFoundation()).quality_preview(request)
    assert report.status == "ready"
    assert report.eligible_for_human_review is True
    assert report.execution_performed is False
    assert report.state_machine_authoritative is True
