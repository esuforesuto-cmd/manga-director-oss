"""Preview Project Intelligence DTOs without scheduling or allocation."""

from manga_director.domain.project import Page, Project
from manga_director.production import V33FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="project-intelligence-demo", title="Project intelligence demo", pages=[Page(page_number=1)]))
report = V33FoundationService(repository).project_intelligence_dashboard(
    "project-intelligence-demo", WorkflowContext(page={"id": "project-intelligence-demo-1"})
)
print(report.to_json())
