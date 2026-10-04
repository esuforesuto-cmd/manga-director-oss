"""Production lifecycle contracts with only local, mock-backed boundaries."""

from __future__ import annotations

from collections.abc import Callable

from manga_director.adapters import ImageBackendRuntime, LLMProviderRuntime
from manga_director.cli.config import AppConfig, configuration_governance
from manga_director.domain.project import Page, Project
from manga_director.observability import RuntimeHealth
from manga_director.production import ProductionMetrics, ProductionRuntime
from manga_director.repositories import InMemoryRepository, RepositorySelfCheck


def _runtime(
    *,
    database_healthy: bool = True,
    metrics: ProductionMetrics | None = None,
    shutdown_hooks: dict[str, Callable[[], None]] | None = None,
) -> ProductionRuntime:
    repository = InMemoryRepository()
    repository.save(Project(id="production", title="Production", pages=[Page(page_number=1)]))
    providers = LLMProviderRuntime()
    backends = ImageBackendRuntime()
    health = RuntimeHealth(
        config=AppConfig(),
        providers=providers,
        backends=backends,
        repository_check=RepositorySelfCheck(repository),
        configuration_summary=lambda: configuration_governance(AppConfig()).model_dump(),
    )
    return ProductionRuntime(
        providers=providers,
        backends=backends,
        health=health,
        configuration=lambda: configuration_governance(AppConfig()).model_dump(),
        dependencies={"database": lambda: database_healthy, "repository": lambda: True},
        shutdown_hooks=shutdown_hooks,
        metrics=metrics,
    )


def test_production_startup_validates_boundaries_and_is_idempotent() -> None:
    runtime = _runtime()

    startup = runtime.start()

    assert startup.ready is True
    assert runtime.start() is startup
    assert startup.provider_warmup["ready"] is True
    assert startup.backend_warmup["ready"] is True
    assert runtime.readiness() is True
    assert runtime.liveness() is True
    assert '"ready": true' in startup.to_json()
    assert "# Startup Report" in startup.to_markdown()


def test_health_and_runtime_reports_are_safe_transport_dtos() -> None:
    metrics = ProductionMetrics()
    runtime = _runtime(metrics=metrics)
    runtime.start()
    metrics.registry.increment("workflow.executions")
    metrics.registry.observe("provider.warmup.duration_seconds", 0.01)

    health = runtime.health_report("production")
    report = runtime.report()

    assert health.live is health.ready is True
    assert health.application.repository["healthy"] is True
    assert report.metrics.workflow["counters"]["workflow.executions"] == 1
    assert report.metrics.provider["durations"]["provider.warmup.duration_seconds"]["count"] == 1
    assert "# Production Health" in health.to_markdown()
    assert "# Production Runtime Report" in report.to_markdown()


def test_failed_dependency_blocks_readiness_without_affecting_liveness() -> None:
    runtime = _runtime(database_healthy=False)

    startup = runtime.start()
    health = runtime.health_report("production")

    assert startup.ready is False
    assert runtime.liveness() is True
    assert health.ready is False
    assert health.database.healthy is False


def test_shutdown_is_graceful_and_retains_cleanup_failures() -> None:
    completed: list[str] = []

    def fail() -> None:
        raise RuntimeError("expected")

    runtime = _runtime(shutdown_hooks={
        "first": lambda: completed.append("first"),
        "failing": fail,
    })

    shutdown = runtime.shutdown()

    assert shutdown.graceful is False
    assert completed == ["first"]
    assert any("failing: expected" in error for error in shutdown.errors)
    assert "backends" in shutdown.completed
    assert "providers" in shutdown.completed


def test_provider_backend_warmup_refresh_and_priority_stay_metadata_only() -> None:
    providers = LLMProviderRuntime()
    backends = ImageBackendRuntime()

    provider_warmup = providers.warmup()
    backend_warmup = backends.warmup()

    assert provider_warmup.ready is True
    assert backend_warmup.ready is True
    assert providers.refresh_metadata()[0].name == "mock"
    assert "mock" in providers.refresh_capabilities()["text"]
    assert providers.evaluate_priority()[0] == "mock"
    assert providers.fallback_simulation().enabled is False
    assert backends.refresh_metadata()[0].name == "mock"
    assert "comfyui" in backends.refresh_capabilities()["workflow"]


def test_production_metrics_collect_all_runtime_categories() -> None:
    metrics = ProductionMetrics()
    metrics.registry.increment("automation.executions")
    metrics.registry.increment("notification.deliveries")
    metrics.registry.observe("repository.load.duration_seconds", 0.01)

    report = metrics.report()

    assert report.automation["counters"]["automation.executions"] == 1
    assert report.notification["counters"]["notification.deliveries"] == 1
    assert report.repository["durations"]["repository.load.duration_seconds"]["count"] == 1
