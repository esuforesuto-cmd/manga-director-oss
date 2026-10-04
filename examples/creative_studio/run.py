"""Preview one Creative Studio DTO; this example never runs a workflow."""

from manga_director.domain.project import Page, Project
from manga_director.production import V32FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="studio-demo", title="Studio demo", pages=[Page(page_number=1)]))
report = V32FoundationService(repository).creative_studio_dashboard(
    "studio-demo", WorkflowContext(page={"id": "studio-demo-1"})
)
print(report.to_json())
