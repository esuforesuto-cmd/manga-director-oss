"""Print a read-only v4 Workspace governance dashboard."""

from manga_director.domain.project import Page, Project
from manga_director.production import V4GovernanceService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def main() -> None:
    repository = InMemoryRepository()
    repository.save(Project(id="example", title="Example", pages=[Page(page_number=1)]))
    print(
        V4GovernanceService(repository)
        .workspace("example", WorkflowContext(page={"id": "example-1"}))
        .to_json()
    )


if __name__ == "__main__":
    main()
