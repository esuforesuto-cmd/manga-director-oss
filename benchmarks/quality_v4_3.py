"""Measure disabled v4.3 quality-assurance DTO construction only."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_3_production_operations import V43ProductionOperationsService
from manga_director.workflow import WorkflowContext


def main() -> None:
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.PROMPT_BUILT)
    service = V43ProductionOperationsService()
    elapsed = timeit(lambda: service.quality_assurance("project", context), number=1_000)
    print(f"quality-assurance projections: {elapsed:.6f}s")


if __name__ == "__main__":
    main()
