"""Preview Asset Lifecycle DTOs without archive, delete, or repository writes."""

from manga_director.domain.project import Page, Project
from manga_director.production import V33FoundationService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(
    Project(
        id="asset-lifecycle-demo",
        title="Asset lifecycle demo",
        pages=[Page(page_number=1)],
        metadata={"reference": {"name": "private"}},
    )
)
report = V33FoundationService(repository).asset_lifecycle_dashboard(
    "asset-lifecycle-demo", WorkflowContext(page={"id": "asset-lifecycle-demo-1"})
)
print(report.to_json())
