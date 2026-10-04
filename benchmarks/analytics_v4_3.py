"""Measure disabled v4.3 project-analytics DTO construction only."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production.v4_3_production_intelligence import V43ProductionIntelligenceService
from manga_director.workflow import WorkflowContext


def main() -> None:
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    service = V43ProductionIntelligenceService()
    elapsed = timeit(lambda: service.project_analytics("project", context), number=1_000)
    print(f"project-analytics projections: {elapsed:.6f}s")


if __name__ == "__main__":
    main()
