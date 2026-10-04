"""Contracts for non-enforcing v5.4 Quality Framework maturity reports."""

from __future__ import annotations

from manga_director.platform import (
    QualityEngineRequestDTO,
    QualityFrameworkMaturityService,
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


def test_quality_governance_is_human_gated_and_non_enforcing() -> None:
    report = QualityFrameworkMaturityService().report(_request())
    assert report.governance.human_review_required is True
    assert report.governance.state_machine_authoritative is True
    assert report.governance.policy_enforced is False
    assert report.governance.automatic_action_taken is False


def test_review_audit_is_ephemeral_and_never_audits_or_persists() -> None:
    report = QualityFrameworkMaturityService().report(_request())
    assert report.review_audit.audit_ready is True
    assert report.review_audit.audit_performed is False
    assert report.review_audit.audit_persisted is False


def test_validation_governance_never_controls_ci_cd() -> None:
    report = QualityFrameworkMaturityService().report(_request())
    assert report.validation_governance.validation_evidence_complete is True
    assert report.validation_governance.validation_policy_compliant is True
    assert report.validation_governance.ci_cd_controlled is False
    assert report.validation_governance.policy_enforced is False


def test_quality_reliability_does_not_operate_health_or_recovery() -> None:
    report = QualityFrameworkMaturityService().report(_request())
    assert report.reliability.metadata_valid is True
    assert report.reliability.health_check_performed is False
    assert report.reliability.recovery_attempted is False
    assert report.reliability.runtime_reconfigured is False


def test_release_lifecycle_is_advisory_and_requires_human_decision() -> None:
    report = UnifiedSDKFoundation().quality_maturity(_request())
    assert report.release_lifecycle.stage == "advisory"
    assert report.release_lifecycle.human_decision_required is True
    assert report.release_lifecycle.lifecycle_transitioned is False
    assert report.release_lifecycle.release_performed is False
