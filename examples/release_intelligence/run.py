"""Preview v3.4 Release Intelligence without tagging, publishing, or deployment."""

from manga_director.domain.project import Page, Project
from manga_director.production import V34FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="release-demo", title="Release demo", pages=[Page(page_number=1)]))
report = V34FoundationService(repository).release_intelligence_dashboard(
    "release-demo", WorkflowContext(page={"id": "release-demo-1"})
)
print(report.to_json())
