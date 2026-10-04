"""Render grouped observability DTOs without executing a workflow."""

from manga_director.domain.project import Page, Project
from manga_director.observability import MetricsRegistry
from manga_director.production import ProductionInsights, RepositoryMaintenance
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def main() -> None:
    repository = InMemoryRepository()
    repository.save(Project(id="observability", title="Observability", pages=[Page(page_number=1)]))
    metrics = MetricsRegistry()
    metrics.increment("repository.operations.load")
    metrics.observe("repository.duration_seconds.load", 0.001)
    report = ProductionInsights(metrics=metrics, maintenance=RepositoryMaintenance(repository)).observability_report(
        WorkflowContext(page={"id": "one"})
    )
    print(report.to_markdown())


if __name__ == "__main__":
    main()
