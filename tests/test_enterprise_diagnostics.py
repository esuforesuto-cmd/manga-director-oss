from manga_director.adapters import ImageBackendRuntime, LLMProviderRuntime
from manga_director.cli.config import AppConfig, configuration_governance
from manga_director.domain.project import Page, Project
from manga_director.observability import (
    EnterpriseDiagnostics,
    HealthMonitor,
    MetricsRegistry,
    PerformanceMonitor,
)
from manga_director.repositories import InMemoryRepository, RepositoryScalability


def test_enterprise_diagnostics_aggregates_safe_transport_neutral_summaries() -> None:
    repository = InMemoryRepository()
    repository.save(Project(id="diagnostics-project", title="Diagnostics", pages=[Page(page_number=1)]))
    metrics = MetricsRegistry()
    metrics.observe("workflow.duration_seconds", 0.01)

    report = EnterpriseDiagnostics(
        config=AppConfig(profile="enterprise", read_only=True),
        providers=LLMProviderRuntime(),
        backends=ImageBackendRuntime(),
        repository=RepositoryScalability(repository),
        performance=PerformanceMonitor(metrics),
        health=HealthMonitor({"repository": lambda: True}),
        configuration_summary=lambda: configuration_governance(
            AppConfig(profile="enterprise", read_only=True)
        ).model_dump(),
    ).report("diagnostics-project")

    assert report.repository_summary["pages"] == 1
    assert report.configuration_summary["compatible"] is True
    assert report.health_summary["healthy"] is True
    assert '"provider_summary"' in report.to_json()
    assert "# Enterprise Diagnostics" in report.to_markdown()
