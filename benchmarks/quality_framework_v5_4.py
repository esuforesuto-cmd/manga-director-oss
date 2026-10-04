"""Measure local v5.4 Quality Framework maturity reporting without actions."""

from timeit import timeit

from manga_director.platform import (
    QualityEngineRequestDTO,
    QualityFrameworkMaturityService,
    QualityPolicyDTO,
    QualityScopeDTO,
    ReleaseCriterionDTO,
    ReviewEvidenceDTO,
    ValidationEvidenceDTO,
)


def _service_and_request() -> tuple[QualityFrameworkMaturityService, QualityEngineRequestDTO]:
    return QualityFrameworkMaturityService(), QualityEngineRequestDTO(
        scope=QualityScopeDTO(
            project_id="benchmark", page_reference="page-001", storyboard_persisted=True
        ),
        policy=QualityPolicyDTO(policy_id="quality", revision="1", owner="quality"),
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


def main() -> None:
    service, request = _service_and_request()
    elapsed = timeit(lambda: service.report(request), number=1_000)
    print(f"quality-framework-v5.4 projections: {elapsed:.6f}s")


if __name__ == "__main__":
    main()
