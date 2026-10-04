"""Measure disabled v4.2 observability DTO construction only."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_2_autonomous_operations import V42AutonomousOperationsService
from manga_director.workflow import WorkflowContext


def main() -> None:
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    service = V42AutonomousOperationsService()
    print(f"monitoring projections: {timeit(lambda: service.observability('project', context), number=1_000):.6f}s")


if __name__ == "__main__":
    main()
