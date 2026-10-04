"""Contracts for repository-backed production operations and diagnostics."""

from __future__ import annotations

from manga_director.adapters import ImageBackendRuntime, LLMProviderRuntime
from manga_director.cli.config import AppConfig, validate_configuration_import
from manga_director.domain.project import Page, Project
from manga_director.production import (
    BackendManagement,
    HealthHistoryStore,
    OperationalDiagnostics,
    ProviderManagement,
    RuntimeConfiguration,
)
from manga_director.repositories import InMemoryRepository


def _history() -> tuple[InMemoryRepository, HealthHistoryStore]:
    repository = InMemoryRepository()
    repository.save(Project(id="operations", title="Operations", pages=[Page(page_number=1)]))
    return repository, HealthHistoryStore(repository, limit=3)


def test_runtime_configuration_snapshot_compare_export_and_import_validation() -> None:
    configuration = RuntimeConfiguration(AppConfig(database_url="sqlite:///local.db"))
    other = AppConfig(profile="enterprise", read_only=True, log_level="WARNING")

    snapshot = configuration.snapshot()
    comparison = configuration.compare(other)
    exported = configuration.export("json")
    imported = configuration.validate_import(exported, "json")

    assert snapshot.values["database_url"] == "[redacted]"
    assert configuration.fingerprint() == configuration.report().governance.fingerprint
    assert "log_level" in comparison.changes
    assert imported.valid is True
    assert validate_configuration_import("[]", "json").valid is False


def test_provider_inventory_reports_priority_capability_and_diagnostic_recommendation() -> None:
    manager = ProviderManagement(LLMProviderRuntime())

    report = manager.inventory(refresh=True, priorities={"openai": 0})

    assert report.providers[0]["name"] == "mock"
    assert "text" in report.capabilities
    assert report.recommendation.available is True
    assert report.recommendation.name == "mock"
    assert "# Provider Inventory" in report.to_markdown()


def test_backend_inventory_reports_presets_and_workflow_compatibility() -> None:
    manager = BackendManagement(ImageBackendRuntime())

    report = manager.inventory(refresh=True)

    assert report.presets["mock"] == ["test"]
    assert next(item for item in report.workflow_compatibility if item["backend"] == "comfyui")[
        "compatible"
    ] is True
    assert all("healthy" in item for item in report.backends)
    assert "# Backend Inventory" in report.to_markdown()


def test_health_history_is_bounded_and_persisted_through_repository_port() -> None:
    repository, history = _history()
    configuration = RuntimeConfiguration(AppConfig())
    providers = ProviderManagement(LLMProviderRuntime())
    backends = BackendManagement(ImageBackendRuntime())

    configuration.record(history, "operations")
    providers.record_health(history, "operations")
    backends.record_health(history, "operations")
    history.record("operations", "runtime", True, {"ignored": "oldest"})

    timeline = history.timeline("operations")

    assert len(timeline.snapshots) == 3
    assert [snapshot.scope for snapshot in timeline.snapshots] == ["provider", "backend", "runtime"]
    assert repository.load("operations").metadata["operational_health_history"]
    assert "# Health Timeline" in timeline.to_markdown()


def test_operational_diagnostics_combines_safe_inventory_and_dependency_reports() -> None:
    _, history = _history()
    configuration = RuntimeConfiguration(AppConfig())
    providers = ProviderManagement(LLMProviderRuntime())
    backends = BackendManagement(ImageBackendRuntime())
    providers.record_health(history, "operations")
    backends.record_health(history, "operations")
    diagnostics = OperationalDiagnostics(
        configuration=configuration,
        providers=providers,
        backends=backends,
        dependencies={"repository": True, "database": True},
        history=history,
    )

    report = diagnostics.report("operations")

    assert report.runtime_summary["healthy"] is True
    assert report.dependencies == {"database": True, "repository": True}
    assert report.providers.health_history
    assert report.backends.health_history
    assert "# Operational Diagnostics" in report.to_markdown()
