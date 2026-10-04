"""Preview one Production Pipeline DTO; this example never runs a workflow."""

from manga_director.domain.project import Page, Project
from manga_director.production import V33FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="pipeline-demo", title="Pipeline demo", pages=[Page(page_number=1)]))
report = V33FoundationService(repository).production_pipeline_dashboard(
    "pipeline-demo", WorkflowContext(page={"id": "pipeline-demo-1"})
)
print(report.to_json())
