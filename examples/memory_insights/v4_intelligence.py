"""Print a read-only Creative Memory intelligence report."""

from manga_director.domain.project import Page, Project
from manga_director.production import V4IntelligenceService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def main() -> None:
    repository = InMemoryRepository()
    repository.save(Project(id="example", title="Example", pages=[Page(page_number=1)]))
    report = V4IntelligenceService(repository).memory(
        "example", WorkflowContext(page={"id": "example-1"})
    )
    print(report.to_json())


if __name__ == "__main__":
    main()
