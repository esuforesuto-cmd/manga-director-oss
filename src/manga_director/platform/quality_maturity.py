"""v5.4 non-enforcing governance, audit, reliability, and lifecycle reports.

These services build on local Quality Foundation and Intelligence evidence only.
They never enforce policy, conduct an audit, control CI/CD, transition a
workflow, approve a Page, recover a runtime, or operate release publication.
"""

from __future__ import annotations

from manga_director.platform.quality import QualityEngineFoundation, QualityEngineRequestDTO
from manga_director.platform.quality_intelligence import (
    ContinuousQualityMonitoringFoundation,
    QualityIntelligenceService,
    QualityObservationDTO,
    ReleaseReadinessDashboardDTO,
)
from manga_director.production.director import DirectorModel


class QualityGovernanceReport(DirectorModel):
    dashboard: ReleaseReadinessDashboardDTO
    policy_id: str
    policy_revision: str
    human_review_required: bool = True
    state_machine_authoritative: bool = True
    policy_enforced: bool = False
    automatic_action_taken: bool = False
    planning_only: bool = True


class ReviewAuditReport(DirectorModel):
    dashboard: ReleaseReadinessDashboardDTO
    supplied_review_count: int = 0
    completed_quality_review_count: int = 0
    audit_ready: bool = False
    audit_performed: bool = False
    audit_persisted: bool = False
    planning_only: bool = True


class ValidationGovernanceReport(DirectorModel):
    dashboard: ReleaseReadinessDashboardDTO
    validation_evidence_complete: bool = False
    validation_policy_compliant: bool = False
    ci_cd_controlled: bool = False
    policy_enforced: bool = False
    planning_only: bool = True


class QualityReliabilityReport(DirectorModel):
    dashboard: ReleaseReadinessDashboardDTO
    metadata_valid: bool = False
    evidence_trend: str
    health_check_performed: bool = False
    recovery_attempted: bool = False
    runtime_reconfigured: bool = False
    planning_only: bool = True


class ReleaseLifecycleReport(DirectorModel):
    dashboard: ReleaseReadinessDashboardDTO
    stage: str = "advisory"
    human_decision_required: bool = True
    lifecycle_transitioned: bool = False
    lifecycle_persisted: bool = False
    release_performed: bool = False
    planning_only: bool = True


class QualityFrameworkMaturityReport(DirectorModel):
    dashboard: ReleaseReadinessDashboardDTO
    governance: QualityGovernanceReport
    review_audit: ReviewAuditReport
    validation_governance: ValidationGovernanceReport
    reliability: QualityReliabilityReport
    release_lifecycle: ReleaseLifecycleReport
    lts_compatible: bool = True
    automatic_action_taken: bool = False
    planning_only: bool = True


class QualityFrameworkMaturityService:
    """Composes non-operational Quality Framework operating-quality evidence."""

    def __init__(
        self,
        engine: QualityEngineFoundation | None = None,
        intelligence: QualityIntelligenceService | None = None,
    ) -> None:
        quality_engine = engine or QualityEngineFoundation()
        self._intelligence = intelligence or QualityIntelligenceService(
            quality_engine, ContinuousQualityMonitoringFoundation()
        )

    def report(
        self,
        request: QualityEngineRequestDTO,
        observations: tuple[QualityObservationDTO, ...] = (),
    ) -> QualityFrameworkMaturityReport:
        dashboard = self._intelligence.preview(request, observations)
        governance = QualityGovernanceReport(
            dashboard=dashboard,
            policy_id=request.policy.policy_id,
            policy_revision=request.policy.revision,
            human_review_required=request.policy.human_sign_off_required,
        )
        review_audit = ReviewAuditReport(
            dashboard=dashboard,
            supplied_review_count=dashboard.review.supplied_review_count,
            completed_quality_review_count=dashboard.review.completed_quality_review_count,
            audit_ready=dashboard.review.status == "ready",
        )
        validation_governance = ValidationGovernanceReport(
            dashboard=dashboard,
            validation_evidence_complete=dashboard.validation.missing_evidence_count == 0,
            validation_policy_compliant=dashboard.validation.status == "ready",
        )
        reliability = QualityReliabilityReport(
            dashboard=dashboard,
            metadata_valid=dashboard.readiness == "ready_for_human_decision",
            evidence_trend=dashboard.monitoring.trend,
        )
        release_lifecycle = ReleaseLifecycleReport(dashboard=dashboard)
        return QualityFrameworkMaturityReport(
            dashboard=dashboard,
            governance=governance,
            review_audit=review_audit,
            validation_governance=validation_governance,
            reliability=reliability,
            release_lifecycle=release_lifecycle,
        )
