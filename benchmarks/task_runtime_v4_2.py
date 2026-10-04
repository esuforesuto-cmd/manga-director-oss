"""Measure disabled v4.2 long-running-task DTO construction only."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_2_autonomous_foundation import V42AutonomousFoundationService
from manga_director.workflow import WorkflowContext


def main() -> None:
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    service = V42AutonomousFoundationService()
    print(
        "long-running task projections: "
        f"{timeit(lambda: service.long_running_tasks('project', context), number=1_000):.6f}s"
    )


if __name__ == "__main__":
    main()
