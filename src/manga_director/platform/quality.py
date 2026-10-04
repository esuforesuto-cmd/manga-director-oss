"""v5.4 local, human-gated Creative Quality Framework foundations.

These DTOs provide diagnostic quality evidence only.  They never execute a
review, mutate a workflow, control CI/CD, approve a Page, or publish a release.
The domain StateMachine remains the sole transition authority.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.production.director import DirectorModel

QualityStatus = Literal["ready", "needs_review", "blocked", "unknown"]
Severity = Literal["info", "warning", "error"]


class QualityScopeDTO(DirectorModel):
    """The single-Page scope to which a quality preview is limited."""

    project_id: str
    page_reference: str
    requested_page_count: Literal[1] = 1
    storyboard_persisted: bool = False


class QualityPolicyDTO(DirectorModel):
    policy_id: str
    revision: str
    owner: str
    required_checks: tuple[str, ...] = ()
    human_sign_off_required: bool = True
    enforcement_performed: bool = False


class ReviewEvidenceDTO(DirectorModel):
    review_id: str
    page_reference: str
    reviewer: str
    completed: bool = False
    quality_review: bool = True
    evidence_reference: str | None = None
    review_executed: bool = False


class ReviewFindingDTO(DirectorModel):
    code: str
    severity: Severity
    message: str


class ReviewPipelineReport(DirectorModel):
    scope: QualityScopeDTO
    reviews: tuple[ReviewEvidenceDTO, ...] = ()
    findings: tuple[ReviewFindingDTO, ...] = ()
    status: QualityStatus = "unknown"
    eligible_for_human_page_approval: bool = False
    state_machine_authoritative: bool = True
    approval_performed: bool = False


class ReviewPipelineFoundation:
    """Evaluates supplied review evidence without conducting a review."""

    def evaluate(
        self, scope: QualityScopeDTO, reviews: tuple[ReviewEvidenceDTO, ...] = ()
    ) -> ReviewPipelineReport:
        findings: list[ReviewFindingDTO] = []
        if not scope.storyboard_persisted:
            findings.append(
                ReviewFindingDTO(
                    code="storyboard_missing",
                    severity="error",
                    message="a persisted storyboard is required before image generation",
                )
            )
        unrelated = tuple(item for item in reviews if item.page_reference != scope.page_reference)
        if unrelated:
            findings.append(
                ReviewFindingDTO(
                    code="review_scope_mismatch",
                    severity="error",
                    message="review evidence must refer to the requested Page",
                )
            )
        completed_quality_review = any(
            item.completed and item.quality_review and item.page_reference == scope.page_reference
            for item in reviews
        )
        if not completed_quality_review:
            findings.append(
                ReviewFindingDTO(
                    code="quality_review_incomplete",
                    severity="error",
                    message="a completed quality review is required before Page approval",
                )
            )
        if findings:
            status: QualityStatus = "blocked"
        else:
            status = "ready"
        return ReviewPipelineReport(
            scope=scope,
            reviews=reviews,
            findings=tuple(findings),
            status=status,
            eligible_for_human_page_approval=status == "ready",
        )


class ValidationEvidenceDTO(DirectorModel):
    validation_id: str
    category: Literal["unit", "integration", "compatibility", "security", "documentation", "package"]
    passed: bool
    evidence_reference: str | None = None
    executed: bool = False
    ci_controlled: bool = False


class ValidationFindingDTO(DirectorModel):
    validation_id: str
    severity: Severity
    message: str


class ValidationEngineReport(DirectorModel):
    validations: tuple[ValidationEvidenceDTO, ...] = ()
    findings: tuple[ValidationFindingDTO, ...] = ()
    status: QualityStatus = "unknown"
    execution_performed: bool = False
    ci_cd_controlled: bool = False


class ValidationEngineFoundation:
    """Normalizes declared validation evidence and makes gaps explicit."""

    def evaluate(self, validations: tuple[ValidationEvidenceDTO, ...] = ()) -> ValidationEngineReport:
        findings: list[ValidationFindingDTO] = []
        if not validations:
            findings.append(
                ValidationFindingDTO(
                    validation_id="validation_inventory",
                    severity="warning",
                    message="no validation evidence was supplied",
                )
            )
            status: QualityStatus = "unknown"
        else:
            for item in validations:
                if not item.evidence_reference:
                    findings.append(
                        ValidationFindingDTO(
                            validation_id=item.validation_id,
                            severity="warning",
                            message="validation evidence reference is missing",
                        )
                    )
                if not item.passed:
                    findings.append(
                        ValidationFindingDTO(
                            validation_id=item.validation_id,
                            severity="error",
                            message="declared validation did not pass",
                        )
                    )
                if item.executed or item.ci_controlled:
                    findings.append(
                        ValidationFindingDTO(
                            validation_id=item.validation_id,
                            severity="warning",
                            message="Foundation accepts evidence only and cannot control execution",
                        )
                    )
            if any(item.severity == "error" for item in findings):
                status = "blocked"
            elif findings:
                status = "needs_review"
            else:
                status = "ready"
        return ValidationEngineReport(
            validations=validations,
            findings=tuple(findings),
            status=status,
        )


class QualityMetricDTO(DirectorModel):
    metric_id: str
    value: float = Field(ge=0)
    unit: Literal["ratio", "count"]
    numerator: int = Field(ge=0)
    denominator: int = Field(ge=0)
    status: QualityStatus
    evidence_references: tuple[str, ...] = ()


class QualityMetricsReport(DirectorModel):
    metrics: tuple[QualityMetricDTO, ...] = ()
    status: QualityStatus = "unknown"
    calculation_performed: bool = True
    workflow_changed: bool = False


class QualityMetricsFoundation:
    """Calculates transparent coverage metrics from supplied validation evidence."""

    def summarize(self, validations: tuple[ValidationEvidenceDTO, ...] = ()) -> QualityMetricsReport:
        denominator = len(validations)
        passed = sum(item.passed for item in validations)
        references = tuple(
            item.evidence_reference for item in validations if item.evidence_reference is not None
        )
        status: QualityStatus
        if not validations:
            status = "unknown"
            value = 0.0
        elif passed == denominator:
            status = "ready"
            value = 1.0
        else:
            status = "needs_review"
            value = passed / denominator
        metric = QualityMetricDTO(
            metric_id="validation_coverage",
            value=value,
            unit="ratio",
            numerator=passed,
            denominator=denominator,
            status=status,
            evidence_references=references,
        )
        return QualityMetricsReport(metrics=(metric,), status=status)


class ReleaseCriterionDTO(DirectorModel):
    criterion_id: str
    category: Literal["quality", "compatibility", "security", "documentation", "package", "approval"]
    satisfied: bool = False
    evidence_reference: str | None = None
    required: bool = True


class ReleaseCriteriaReport(DirectorModel):
    policy: QualityPolicyDTO
    criteria: tuple[ReleaseCriterionDTO, ...] = ()
    status: QualityStatus = "unknown"
    eligible_for_human_release_decision: bool = False
    release_performed: bool = False
    lts_compatibility_required: bool = True


class ReleaseCriteriaFoundation:
    """Summarizes release criteria without changing the release process."""

    def evaluate(
        self, policy: QualityPolicyDTO, criteria: tuple[ReleaseCriterionDTO, ...] = ()
    ) -> ReleaseCriteriaReport:
        required = tuple(item for item in criteria if item.required)
        has_required_approval = any(item.category == "approval" for item in required)
        if not required:
            status: QualityStatus = "unknown"
        elif policy.human_sign_off_required and not has_required_approval:
            status = "blocked"
        elif all(item.satisfied and item.evidence_reference for item in required):
            status = "ready"
        else:
            status = "blocked"
        return ReleaseCriteriaReport(
            policy=policy,
            criteria=criteria,
            status=status,
            eligible_for_human_release_decision=status == "ready" and policy.human_sign_off_required,
        )


class QualityEngineRequestDTO(DirectorModel):
    scope: QualityScopeDTO
    policy: QualityPolicyDTO
    reviews: tuple[ReviewEvidenceDTO, ...] = ()
    validations: tuple[ValidationEvidenceDTO, ...] = ()
    release_criteria: tuple[ReleaseCriterionDTO, ...] = ()


class QualityEngineReport(DirectorModel):
    review: ReviewPipelineReport
    validation: ValidationEngineReport
    metrics: QualityMetricsReport
    release_criteria: ReleaseCriteriaReport
    status: QualityStatus
    findings: tuple[str, ...] = ()
    eligible_for_human_review: bool = False
    execution_performed: bool = False
    state_machine_authoritative: bool = True
    planning_only: bool = True


class QualityEngineFoundation:
    """Composes read-only quality reports into a single human review packet."""

    def __init__(
        self,
        review_pipeline: ReviewPipelineFoundation | None = None,
        validation_engine: ValidationEngineFoundation | None = None,
        metrics: QualityMetricsFoundation | None = None,
        release_criteria: ReleaseCriteriaFoundation | None = None,
    ) -> None:
        self._review_pipeline = review_pipeline or ReviewPipelineFoundation()
        self._validation_engine = validation_engine or ValidationEngineFoundation()
        self._metrics = metrics or QualityMetricsFoundation()
        self._release_criteria = release_criteria or ReleaseCriteriaFoundation()

    def preview(self, request: QualityEngineRequestDTO) -> QualityEngineReport:
        review = self._review_pipeline.evaluate(request.scope, request.reviews)
        validation = self._validation_engine.evaluate(request.validations)
        metrics = self._metrics.summarize(request.validations)
        criteria = self._release_criteria.evaluate(request.policy, request.release_criteria)
        component_statuses = (review.status, validation.status, metrics.status, criteria.status)
        if "blocked" in component_statuses:
            status: QualityStatus = "blocked"
        elif "unknown" in component_statuses:
            status = "unknown"
        elif "needs_review" in component_statuses:
            status = "needs_review"
        else:
            status = "ready"
        findings = tuple(
            item.message for item in review.findings
        ) + tuple(item.message for item in validation.findings)
        return QualityEngineReport(
            review=review,
            validation=validation,
            metrics=metrics,
            release_criteria=criteria,
            status=status,
            findings=findings,
            eligible_for_human_review=status == "ready",
        )
