"""Measure disabled v4.6 Creative Intelligence analysis DTO construction."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production import V46IntelligenceService
from manga_director.workflow import WorkflowContext


def main() -> None:
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    service = V46IntelligenceService()
    elapsed = timeit(lambda: service.intelligence_dashboard("project", context), number=1_000)
    print(f"intelligence-analysis projections: {elapsed:.6f}s")


if __name__ == "__main__":
    main()
