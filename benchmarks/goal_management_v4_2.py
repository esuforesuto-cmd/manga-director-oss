"""Measure disabled v4.2 Goal Management DTO construction only."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_2_autonomous_workflow import V42AutonomousWorkflowService
from manga_director.workflow import WorkflowContext


def main() -> None:
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    service = V42AutonomousWorkflowService()
    print(
        "goal-management projections: "
        f"{timeit(lambda: service.goal_management('project', context, 'Human review'), number=1_000):.6f}s"
    )


if __name__ == "__main__":
    main()
