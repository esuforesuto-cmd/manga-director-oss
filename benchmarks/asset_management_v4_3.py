"""Measure disabled v4.3 asset-management DTO construction only."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_3_production_foundation import V43ProductionFoundationService
from manga_director.workflow import WorkflowContext


def main() -> None:
    context = WorkflowContext(
        page={"id": "page-1"}, state=PageState.DRAFT, artifacts={"storyboard": {}}
    )
    service = V43ProductionFoundationService()
    elapsed = timeit(lambda: service.asset_management("project", context), number=1_000)
    print(f"asset-management projections: {elapsed:.6f}s")


if __name__ == "__main__":
    main()
