"""Render a planning-only operations report without scheduling any task."""

from manga_director.domain.project import Page, Project
from manga_director.observability import MetricsRegistry
from manga_director.production import ProductionInsights, RepositoryMaintenance
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def main() -> None:
    repository = InMemoryRepository()
    repository.save(Project(id="operations", title="Operations", pages=[Page(page_number=1)]))
    report = ProductionInsights(metrics=MetricsRegistry(), maintenance=RepositoryMaintenance(repository)).operations_report(
        WorkflowContext(page={"id": "one"}), project_id="operations"
    )
    print(report.to_markdown())


if __name__ == "__main__":
    main()
