"""Measure disabled v4.6 intelligence-governance DTO construction."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production import V46IntelligenceGovernanceService
from manga_director.workflow import WorkflowContext


def main() -> None:
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    service = V46IntelligenceGovernanceService()
    elapsed = timeit(lambda: service.operations_validation("project", context), number=1_000)
    print(f"intelligence-governance projections: {elapsed:.6f}s")


if __name__ == "__main__":
    main()
