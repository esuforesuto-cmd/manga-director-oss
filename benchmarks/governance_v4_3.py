"""Measure disabled v4.3 production-governance DTO construction only."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_3_production_operations import V43ProductionOperationsService
from manga_director.workflow import WorkflowContext


def main() -> None:
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    service = V43ProductionOperationsService()
    elapsed = timeit(lambda: service.production_governance("project", context), number=1_000)
    print(f"production-governance projections: {elapsed:.6f}s")


if __name__ == "__main__":
    main()
