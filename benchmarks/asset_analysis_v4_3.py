"""Measure disabled v4.3 asset-analysis DTO construction only."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_3_production_intelligence import V43ProductionIntelligenceService
from manga_director.workflow import WorkflowContext


def main() -> None:
    context = WorkflowContext(
        page={"id": "page-1"}, state=PageState.DRAFT, artifacts={"storyboard": {}}
    )
    service = V43ProductionIntelligenceService()
    elapsed = timeit(lambda: service.asset_intelligence("project", context), number=1_000)
    print(f"asset-analysis projections: {elapsed:.6f}s")


if __name__ == "__main__":
    main()
