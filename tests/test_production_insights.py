"""Contracts for the v2.5 Iteration 2 read-only insights facade."""

from __future__ import annotations

from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState
from manga_director.observability import MetricsRegistry
from manga_director.production import PerformanceBaseline, ProductionInsights, RepositoryMaintenance
from manga_director.repositories import InMemoryRepository
from manga_director.workflow import WorkflowContext


def _insights() -> tuple[ProductionInsights, MetricsRegistry]:
    repository = InMemoryRepository()
    repository.save(Project(id="insights", title="Insights", pages=[Page(page_number=1)]))
    metrics = MetricsRegistry()
    return ProductionInsights(metrics=metrics, maintenance=RepositoryMaintenance(repository)), metrics


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "one"},
        state=PageState.DESIGNED,
        metadata={
            "workflow_history": [
                {"kind": "workflow", "from": "Draft", "to": "Designed", "step": "design"}
            ]
        },
    )


def test_observability_report_groups_metrics_and_builds_timelines() -> None:
    insights, metrics = _insights()
    for category in ("repository", "provider", "backend", "automation", "release"):
        metrics.increment(f"{category}.operations")
        metrics.observe(f"{category}.duration_seconds", 0.01)

    report = insights.observability_report(
        _context(), [{"name": "repository_check", "status": "planned", "duration_seconds": 0.02}]
    )

    assert report.workflow_timeline.entries[0].name == "design"
    assert report.operation_timeline.entries[0].status == "planned"
    assert report.repository_metrics["counters"]["repository.operations"] == 1
    assert report.release_metrics["durations"]["release.duration_seconds"]["count"] == 1
    assert "# Observability Report" in report.to_markdown()


def test_diagnostics_report_exposes_safe_system_repository_and_performance_sections() -> None:
    insights, metrics = _insights()
    metrics.observe("repository.load.duration_seconds", 0.01)

    report = insights.diagnostics_report(
        _context(),
        configuration={"profile": "production"},
        environment={"workspace": "local"},
        project_id="insights",
    )

    assert report.system["network_probes"] is False
    assert report.repository["consistency"]["healthy"] is True
    assert report.configuration["profile"] == "production"
    assert "# Diagnostics Report" in report.to_markdown()


def test_performance_analysis_detects_regression_and_reports_trends_without_optimizing() -> None:
    insights, metrics = _insights()
    metrics.observe("repository.load.duration_seconds", 0.03)

    report = insights.performance_report(
        baseline=PerformanceBaseline(name="baseline", averages_seconds={"repository.load.duration_seconds": 0.01}),
        history={"repository.load.duration_seconds": [0.01, 0.02, 0.03]},
    )

    assert report.regression.regressed is True
    assert report.comparisons[0].metric == "repository.load.duration_seconds"
    assert report.trends[0].direction == "regressing"
    assert report.recommendations[0].message.startswith("Investigate")
    assert "# Performance Report" in report.to_markdown()


def test_operations_summary_is_planning_only_and_never_deletes_projects() -> None:
    insights, _ = _insights()

    report = insights.operations_report(_context(), project_id="insights")
    summary = insights.executive_summary(_context(), project_id="insights")

    assert report.scheduler_plan.automatic_execution is False
    assert report.cleanup_plan.execution_performed is False
    assert report.maintenance.statistics.projects == 1
    assert summary.planned_automation is False
    assert summary.repository_healthy is True
    assert "# Operations Report" in report.to_markdown()


def test_performance_trend_and_empty_operation_timeline_are_bounded() -> None:
    insights, _ = _insights()

    report = insights.performance_report(history={"workflow.step": [0.02, 0.01]})
    timeline = insights.operation_timeline()

    assert report.trends[0].direction == "improving"
    assert timeline.entries == ()
