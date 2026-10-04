"""Measure disabled v4.5 ecosystem-foundation DTO construction only."""

from timeit import timeit

from manga_director.domain.state_machine import PageState
from manga_director.production import V45EcosystemFoundationService
from manga_director.workflow import WorkflowContext


def main() -> None:
    context = WorkflowContext(page={"id": "page-1"}, state=PageState.DRAFT)
    service = V45EcosystemFoundationService()
    elapsed = timeit(lambda: service.creative_service_registry("project", context), number=1_000)
    print(f"ecosystem-foundation projections: {elapsed:.6f}s")


if __name__ == "__main__":
    main()
