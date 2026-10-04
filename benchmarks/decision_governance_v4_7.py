"""Measure v4.7 Decision Governance DTO construction without execution."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production import V47DecisionGovernanceService
from manga_director.workflow import WorkflowContext


def main() -> None:
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    service = V47DecisionGovernanceService()
    elapsed = timeit(
        lambda: service.executive_decision_governance_dashboard("project", context), number=1_000
    )
    print(f"decision-governance projections: {elapsed:.6f}s")


if __name__ == "__main__":
    main()
