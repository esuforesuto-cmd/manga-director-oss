"""Measure disabled v4.4 enterprise-intelligence DTO construction only."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production import V44EnterpriseIntelligenceService
from manga_director.workflow import WorkflowContext


def main() -> None:
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    service = V44EnterpriseIntelligenceService()
    elapsed = timeit(lambda: service.enterprise_dashboard("project", context), number=1_000)
    print(f"enterprise-intelligence projections: {elapsed:.6f}s")


if __name__ == "__main__":
    main()
