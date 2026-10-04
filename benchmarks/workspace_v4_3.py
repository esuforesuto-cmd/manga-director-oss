"""Measure disabled v4.3 workspace DTO construction only."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_3_production_foundation import V43ProductionFoundationService
from manga_director.workflow import WorkflowContext


def main() -> None:
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    service = V43ProductionFoundationService()
    elapsed = timeit(lambda: service.project_workspace("project", context), number=1_000)
    print(f"workspace projections: {elapsed:.6f}s")


if __name__ == "__main__":
    main()
