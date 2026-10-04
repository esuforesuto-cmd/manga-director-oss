"""Measure v4.7 Decision Intelligence DTO construction without execution."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production import V47DecisionIntelligenceService
from manga_director.workflow import WorkflowContext


def main() -> None:
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    service = V47DecisionIntelligenceService()
    elapsed = timeit(lambda: service.executive_decision_dashboard("project", context), number=1_000)
    print(f"decision-intelligence projections: {elapsed:.6f}s")


if __name__ == "__main__":
    main()
