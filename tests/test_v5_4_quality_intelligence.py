"""Contracts for non-operational v5.4 Quality Intelligence."""

from __future__ import annotations

from manga_director.platform import (
    ContinuousQualityMonitoringFoundation,
    QualityEngineRequestDTO,
    QualityIntelligenceService,
    QualityObservationDTO,
    QualityPolicyDTO,
    QualityScopeDTO,
    ReleaseCriterionDTO,
    ReviewEvidenceDTO,
    UnifiedSDKFoundation,
    ValidationEvidenceDTO,
)


def _request() -> QualityEngineRequestDTO:
    return QualityEngineRequestDTO(
        scope=QualityScopeDTO(
            project_id="project-001", page_reference="page-001", storyboard_persisted=True
        ),
        policy=QualityPolicyDTO(policy_id="quality", revision="1", owner="quality-team"),
        reviews=(
            ReviewEvidenceDTO(
                review_id="review", page_reference="page-001", reviewer="editor", completed=True,
                evidence_reference="reviews/review",
            ),
        ),
        validations=(
            ValidationEvidenceDTO(
                validation_id="compatibility", category="compatibility", passed=True,
                evidence_reference="tests/compatibility",
            ),
        ),
        release_criteria=(
            ReleaseCriterionDTO(
                criterion_id="compatibility", category="compatibility", satisfied=True,
                evidence_reference="tests/compatibility",
            ),
            ReleaseCriterionDTO(
                criterion_id="approval", category="approval", satisfied=True,
                evidence_reference="approvals/release-owner",
            ),
        ),
    )


def test_quality_intelligence_is_advisory_and_has_no_workflow_action() -> None:
    dashboard = QualityIntelligenceService().preview(_request())
    assert dashboard.quality.quality_score == 1.0
    assert dashboard.quality.workflow_changed is False
    assert dashboard.automatic_action_taken is False


def test_review_analytics_counts_matching_completed_reviews_only() -> None:
    dashboard = QualityIntelligenceService().preview(_request())
    assert dashboard.review.supplied_review_count == 1
    assert dashboard.review.completed_quality_review_count == 1
    assert dashboard.review.review_executed is False


def test_validation_intelligence_exposes_incomplete_evidence_without_ci_control() -> None:
    request = _request().model_copy(
        update={
            "validations": (
                ValidationEvidenceDTO(
                    validation_id="security", category="security", passed=False
                ),
            )
        }
    )
    dashboard = QualityIntelligenceService().preview(request)
    assert dashboard.validation.failed_validation_count == 1
    assert dashboard.validation.missing_evidence_count == 1
    assert dashboard.validation.ci_cd_controlled is False
    assert dashboard.readiness == "blocked"


def test_release_readiness_dashboard_is_human_gated() -> None:
    dashboard = QualityIntelligenceService().preview(_request())
    assert dashboard.readiness == "ready_for_human_decision"
    assert dashboard.eligible_for_human_release_decision is True
    assert dashboard.automatic_action_taken is False


def test_continuous_monitoring_is_a_non_persistent_snapshot_summary() -> None:
    monitoring = ContinuousQualityMonitoringFoundation().summarize(
        "ready", (QualityObservationDTO(observation_id="before", status="needs_review"),)
    )
    assert monitoring.trend == "improving"
    assert monitoring.monitoring_started is False
    assert monitoring.persistence_performed is False
    dashboard = UnifiedSDKFoundation().quality_dashboard(_request())
    assert dashboard.monitoring.monitoring_started is False
