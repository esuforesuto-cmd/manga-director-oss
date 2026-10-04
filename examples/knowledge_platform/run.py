"""Preview v3.4 Knowledge Platform DTOs without writes or remote search."""

from manga_director.domain.project import Page, Project
from manga_director.production import V34FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="knowledge-demo", title="Knowledge demo", pages=[Page(page_number=1)]))
report = V34FoundationService(repository).knowledge_platform_dashboard(
    "knowledge-demo", WorkflowContext(page={"id": "knowledge-demo-1"})
)
print(report.to_json())
