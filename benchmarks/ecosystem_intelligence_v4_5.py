"""Measure disabled v4.5 ecosystem-intelligence DTO construction only."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production import V45EcosystemIntelligenceService
from manga_director.workflow import WorkflowContext


def main() -> None:
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    service = V45EcosystemIntelligenceService()
    elapsed = timeit(lambda: service.ecosystem_dashboard("project", context), number=1_000)
    print(f"ecosystem-intelligence projections: {elapsed:.6f}s")


if __name__ == "__main__":
    main()
