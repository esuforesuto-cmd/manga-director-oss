"""Render the four v3.4 governance dashboards without applying policy."""

from manga_director.domain.project import Page, Project
from manga_director.production import V34FoundationService, V34GovernanceService, V34InsightsService
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext

repository = InMemoryRepository()
repository.save(
    Project(id="governance-dashboard", title="Governance dashboard", pages=[Page(page_number=1)])
)
foundation = V34FoundationService(repository)
service = V34GovernanceService(foundation, V34InsightsService(foundation, repository), repository)
context = WorkflowContext(page={"id": "governance-1"})
print(
    {
        "knowledge": service.knowledge_governance_dashboard(
            "governance-dashboard", context
        ).model_dump(),
        "production": service.production_governance_dashboard(
            "governance-dashboard", context
        ).model_dump(),
        "organization": service.organization_governance_dashboard(
            "governance-dashboard", context
        ).model_dump(),
        "release": service.release_governance_dashboard(
            "governance-dashboard", context
        ).model_dump(),
    }
)
