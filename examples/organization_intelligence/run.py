"""Preview v3.4 Organization Intelligence without personnel action."""

from manga_director.domain.project import Page, Project
from manga_director.production import V34FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(Project(id="organization-demo", title="Organization demo", pages=[Page(page_number=1)]))
report = V34FoundationService(repository).organization_intelligence_dashboard(
    "organization-demo", WorkflowContext(page={"id": "organization-demo-1"})
)
print(report.to_json())
