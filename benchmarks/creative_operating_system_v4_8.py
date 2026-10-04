"""Measure v4.8 Creative Operating System report composition without action."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production import V48CreativeOperatingSystemGovernanceService
from manga_director.workflow import WorkflowContext


def main() -> None:
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    service = V48CreativeOperatingSystemGovernanceService()
    elapsed = timeit(lambda: service.creative_operating_system("project", context), number=1_000)
    print(f"creative-operating-system projections: {elapsed:.6f}s")


if __name__ == "__main__":
    main()
