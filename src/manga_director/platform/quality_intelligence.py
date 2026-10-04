"""v5.4 read-only Quality Intelligence diagnostics.

The services in this module analyze caller-supplied Quality Foundation reports.
They do not execute reviews or validations, persist observations, control CI/CD,
change workflow state, approve Pages, or publish releases.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.platform.quality import (
    QualityEngineFoundation,
    QualityEngineReport,
    QualityEngineRequestDTO,
    QualityStatus,
)
from manga_director.production.director import DirectorModel

ReadinessStatus = Literal["ready_for_human_decision", "attention_required", "blocked", "unknown"]


class QualityIntelligenceDTO(DirectorModel):
    status: QualityStatus
    quality_score: float = Field(ge=0, le=1)
    finding_count: int = Field(ge=0)
    recommendation: str
    workflow_changed: bool = False
    planning_only: bool = True


class ReviewAnalyticsDTO(DirectorModel):
    supplied_review_count: int = Field(ge=0)
    completed_quality_review_count: int = Field(ge=0)
    matching_review_count: int = Field(ge=0)
    status: QualityStatus
    recommendation: str
    review_executed: bool = False
    planning_only: bool = True


class ValidationIntelligenceDTO(DirectorModel):
    supplied_validation_count: int = Field(ge=0)
    passed_validation_count: int = Field(ge=0)
    failed_validation_count: int = Field(ge=0)
    missing_evidence_count: int = Field(ge=0)
    status: QualityStatus
    recommendation: str
    ci_cd_controlled: bool = False
    planning_only: bool = True


class QualityObservationDTO(DirectorModel):
    """A caller-supplied immutable observation; no monitoring loop is started."""

    observation_id: str
    status: QualityStatus
    evidence_reference: str | None = None


class ContinuousQualityMonitoringReport(DirectorModel):
    observations: tuple[QualityObservationDTO, ...] = ()
    observation_count: int = Field(ge=0)
    current_status: QualityStatus
    trend: Literal["stable", "improving", "degrading", "unknown"]
    recommendation: str
    monitoring_started: bool = False
    persistence_performed: bool = False
    planning_only: bool = True


class ContinuousQualityMonitoringFoundation:
    """Summarizes supplied snapshots without scheduling or retaining monitoring."""

    def summarize(
        self,
        current_status: QualityStatus,
        observations: tuple[QualityObservationDTO, ...] = (),
    ) -> ContinuousQualityMonitoringReport:
        if not observations:
            trend: Literal["stable", "improving", "degrading", "unknown"] = "unknown"
            recommendation = "supply a later quality snapshot before interpreting a trend"
        elif observations[-1].status == current_status:
            trend = "stable"
            recommendation = "retain human review of the current quality evidence"
        elif current_status == "ready":
            trend = "improving"
            recommendation = "confirm the improvement with an authorized human review"
        else:
            trend = "degrading"
            recommendation = "review changed evidence before making a quality decision"
        return ContinuousQualityMonitoringReport(
            observations=observations,
            observation_count=len(observations),
            current_status=current_status,
            trend=trend,
            recommendation=recommendation,
        )


class ReleaseReadinessDashboardDTO(DirectorModel):
    quality: QualityIntelligenceDTO
    review: ReviewAnalyticsDTO
    validation: ValidationIntelligenceDTO
    monitoring: ContinuousQualityMonitoringReport
    readiness: ReadinessStatus
    recommendation: str
    eligible_for_human_release_decision: bool = False
    automatic_action_taken: bool = False
    planning_only: bool = True


class QualityIntelligenceService:
    """Creates an evidence-led dashboard from the Quality Engine preview."""

    def __init__(
        self,
        engine: QualityEngineFoundation | None = None,
        monitoring: ContinuousQualityMonitoringFoundation | None = None,
    ) -> None:
        self._engine = engine or QualityEngineFoundation()
        self._monitoring = monitoring or ContinuousQualityMonitoringFoundation()

    def preview(
        self,
        request: QualityEngineRequestDTO,
        observations: tuple[QualityObservationDTO, ...] = (),
    ) -> ReleaseReadinessDashboardDTO:
        report = self._engine.preview(request)
        quality = self._quality(report)
        review = self._review(report)
        validation = self._validation(report)
        monitoring = self._monitoring.summarize(report.status, observations)
        readiness, recommendation = self._readiness(report)
        return ReleaseReadinessDashboardDTO(
            quality=quality,
            review=review,
            validation=validation,
            monitoring=monitoring,
            readiness=readiness,
            recommendation=recommendation,
            eligible_for_human_release_decision=(
                readiness == "ready_for_human_decision"
                and report.release_criteria.eligible_for_human_release_decision
            ),
        )

    @staticmethod
    def _quality(report: QualityEngineReport) -> QualityIntelligenceDTO:
        scores: dict[QualityStatus, float] = {
            "ready": 1.0,
            "needs_review": 0.5,
            "blocked": 0.0,
            "unknown": 0.0,
        }
        return QualityIntelligenceDTO(
            status=report.status,
            quality_score=scores[report.status],
            finding_count=len(report.findings),
            recommendation=(
                "present evidence to an authorized human reviewer"
                if report.status == "ready"
                else "resolve or document quality findings before a human decision"
            ),
        )

    @staticmethod
    def _review(report: QualityEngineReport) -> ReviewAnalyticsDTO:
        reviews = report.review.reviews
        matching = tuple(
            item for item in reviews if item.page_reference == report.review.scope.page_reference
        )
        completed = sum(item.completed and item.quality_review for item in matching)
        return ReviewAnalyticsDTO(
            supplied_review_count=len(reviews),
            completed_quality_review_count=completed,
            matching_review_count=len(matching),
            status=report.review.status,
            recommendation=(
                "retain completed review evidence for human approval"
                if report.review.status == "ready"
                else "complete a matching quality review and retain its evidence"
            ),
        )

    @staticmethod
    def _validation(report: QualityEngineReport) -> ValidationIntelligenceDTO:
        validations = report.validation.validations
        passed = sum(item.passed for item in validations)
        missing = sum(item.evidence_reference is None for item in validations)
        return ValidationIntelligenceDTO(
            supplied_validation_count=len(validations),
            passed_validation_count=passed,
            failed_validation_count=len(validations) - passed,
            missing_evidence_count=missing,
            status=report.validation.status,
            recommendation=(
                "retain validation evidence for the human release decision"
                if report.validation.status == "ready"
                else "review failed or incomplete validation evidence"
            ),
        )

    @staticmethod
    def _readiness(report: QualityEngineReport) -> tuple[ReadinessStatus, str]:
        if report.status == "ready":
            return "ready_for_human_decision", "human authorization remains required"
        if report.status == "blocked":
            return "blocked", "do not make a release decision until blocking evidence is resolved"
        if report.status == "unknown":
            return "unknown", "collect declared evidence before assessing release readiness"
        return "attention_required", "review advisory findings with an authorized human"
