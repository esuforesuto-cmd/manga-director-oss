"""Repository-backed, transport-neutral operations helpers outside Core."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from manga_director.adapters.runtime import ImageBackendRuntime, LLMProviderRuntime
from manga_director.cli.config import (
    AppConfig,
    ConfigurationDiff,
    ConfigurationGovernanceReport,
    ConfigurationImportValidation,
    ConfigurationSnapshot,
    configuration_diff,
    configuration_fingerprint,
    configuration_governance,
    configuration_snapshot,
    export_configuration,
    validate_configuration_import,
)
from manga_director.repositories.protocols import ProjectRepository

_HISTORY_KEY = "operational_health_history"


class OperationalHealthSnapshot(BaseModel):
    """A bounded, persisted health event attached to an existing Project aggregate."""

    model_config = ConfigDict(frozen=True)

    scope: Literal["configuration", "provider", "backend", "runtime"]
    healthy: bool
    captured_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, Any] = Field(default_factory=dict)


class HealthTimeline(BaseModel):
    """Safe operational history returned through the Repository port."""

    project_id: str
    scope: str | None = None
    snapshots: list[OperationalHealthSnapshot] = Field(default_factory=list)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown("Health Timeline", self.model_dump(mode="json"))


class HealthHistoryStore:
    """Persist bounded operational snapshots in Project metadata through ProjectRepository."""

    def __init__(self, repository: ProjectRepository, *, limit: int = 100) -> None:
        if limit < 1:
            raise ValueError("Health history limit must be at least one.")
        self._repository = repository
        self._limit = limit

    def record(
        self,
        project_id: str,
        scope: Literal["configuration", "provider", "backend", "runtime"],
        healthy: bool,
        details: Mapping[str, Any],
    ) -> OperationalHealthSnapshot:
        snapshot = OperationalHealthSnapshot(scope=scope, healthy=healthy, details=dict(details))
        project = self._repository.load(project_id)
        raw_history = project.metadata.get(_HISTORY_KEY, [])
        history = raw_history if isinstance(raw_history, list) else []
        metadata = {
            **project.metadata,
            _HISTORY_KEY: [*history, snapshot.model_dump(mode="json")][-self._limit :],
        }
        self._repository.save(project.model_copy(update={"metadata": metadata}, deep=True))
        return snapshot

    def timeline(self, project_id: str, scope: str | None = None) -> HealthTimeline:
        project = self._repository.load(project_id)
        raw_history = project.metadata.get(_HISTORY_KEY, [])
        snapshots: list[OperationalHealthSnapshot] = []
        if isinstance(raw_history, list):
            for item in raw_history:
                try:
                    snapshot = OperationalHealthSnapshot.model_validate(item)
                except ValidationError:
                    continue
                if scope is None or snapshot.scope == scope:
                    snapshots.append(snapshot)
        return HealthTimeline(project_id=project_id, scope=scope, snapshots=snapshots)


class RuntimeConfigurationReport(BaseModel):
    """Snapshot, validation, and fingerprint evidence for runtime configuration."""

    snapshot: ConfigurationSnapshot
    governance: ConfigurationGovernanceReport

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown("Runtime Configuration", self.model_dump(mode="json"))


class RuntimeConfiguration:
    """Application-facing facade over the stable Configuration Layer API."""

    def __init__(self, config: AppConfig, source: Path | None = None) -> None:
        self._config = config
        self._source = source

    def validate(self) -> ConfigurationGovernanceReport:
        return configuration_governance(self._config)

    def snapshot(self) -> ConfigurationSnapshot:
        return configuration_snapshot(self._config, self._source)

    def compare(self, other: AppConfig) -> ConfigurationDiff:
        return configuration_diff(self._config, other)

    def fingerprint(self) -> str:
        return configuration_fingerprint(self._config)

    def export(self, format: Literal["json", "yaml"] = "yaml") -> str:
        return export_configuration(self.snapshot(), format)

    def validate_import(
        self, content: str, format: Literal["json", "yaml"] = "yaml"
    ) -> ConfigurationImportValidation:
        return validate_configuration_import(content, format)

    def report(self) -> RuntimeConfigurationReport:
        return RuntimeConfigurationReport(snapshot=self.snapshot(), governance=self.validate())

    def record(self, history: HealthHistoryStore, project_id: str) -> OperationalHealthSnapshot:
        report = self.report()
        return history.record(
            project_id,
            "configuration",
            report.governance.compatible and report.governance.integrity_valid,
            report.model_dump(mode="json"),
        )


class ProviderRecommendation(BaseModel):
    """Diagnostic-only provider recommendation; it does not select a Provider."""

    name: str | None = None
    available: bool
    reason: str


class ProviderInventoryReport(BaseModel):
    """Provider registry inventory and local construction health evidence."""

    providers: list[dict[str, Any]] = Field(default_factory=list)
    capabilities: dict[str, list[str]] = Field(default_factory=dict)
    priority_order: list[str] = Field(default_factory=list)
    recommendation: ProviderRecommendation
    health_history: list[OperationalHealthSnapshot] = Field(default_factory=list)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown("Provider Inventory", self.model_dump(mode="json"))


class ProviderManagement:
    """Provider operations facade that only reads Factory metadata and local health."""

    def __init__(self, runtime: LLMProviderRuntime) -> None:
        self._runtime = runtime

    def inventory(
        self,
        *,
        refresh: bool = False,
        priorities: Mapping[str, int] | None = None,
        history: HealthHistoryStore | None = None,
        project_id: str | None = None,
    ) -> ProviderInventoryReport:
        inventory = self._runtime.inventory(refresh=refresh)
        health = {item.name: item for item in inventory.health}
        providers = []
        for item in self._runtime.priority_inventory(priorities):
            status = health.get(item.name)
            providers.append({**item.model_dump(mode="json"), "healthy": status.healthy if status else False})
        candidate = next((item for item in providers if item["healthy"]), None)
        recommendation = ProviderRecommendation(
            name=str(candidate["name"]) if candidate else None,
            available=candidate is not None,
            reason="lowest diagnostic priority among locally healthy providers"
            if candidate
            else "no locally healthy provider is registered",
        )
        timeline = history.timeline(project_id, "provider").snapshots if history and project_id else []
        return ProviderInventoryReport(
            providers=providers,
            capabilities=inventory.capabilities,
            priority_order=[str(item["name"]) for item in providers],
            recommendation=recommendation,
            health_history=timeline,
        )

    def record_health(self, history: HealthHistoryStore, project_id: str) -> OperationalHealthSnapshot:
        report = self.inventory()
        return history.record(
            project_id,
            "provider",
            report.recommendation.available,
            report.model_dump(mode="json", exclude={"health_history"}),
        )


class BackendInventoryReport(BaseModel):
    """Image-backend metadata, preset, and workflow-compatibility evidence."""

    backends: list[dict[str, Any]] = Field(default_factory=list)
    capabilities: dict[str, list[str]] = Field(default_factory=dict)
    presets: dict[str, list[str]] = Field(default_factory=dict)
    workflow_compatibility: list[dict[str, Any]] = Field(default_factory=list)
    health_history: list[OperationalHealthSnapshot] = Field(default_factory=list)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown("Backend Inventory", self.model_dump(mode="json"))


class BackendManagement:
    """Image-backend operations facade with no image-generation responsibility."""

    def __init__(self, runtime: ImageBackendRuntime) -> None:
        self._runtime = runtime

    def inventory(
        self,
        *,
        refresh: bool = False,
        history: HealthHistoryStore | None = None,
        project_id: str | None = None,
    ) -> BackendInventoryReport:
        inventory = self._runtime.inventory(refresh=refresh)
        health = {item.name: item for item in inventory.health}
        backends = []
        for item in self._runtime.priority_inventory():
            status = health.get(item.name)
            backends.append({**item.model_dump(mode="json"), "healthy": status.healthy if status else False})
        compatibility = [
            self._runtime.workflow_compatibility_report(
                item.name, {"format": item.workflow_metadata.get("format")}
            )
            if item.workflow_metadata
            else {"backend": item.name, "compatible": True, "messages": ["no workflow metadata declared"]}
            for item in self._runtime.discover()
        ]
        timeline = history.timeline(project_id, "backend").snapshots if history and project_id else []
        return BackendInventoryReport(
            backends=backends,
            capabilities=inventory.capabilities,
            presets=inventory.presets,
            workflow_compatibility=compatibility,
            health_history=timeline,
        )

    def record_health(self, history: HealthHistoryStore, project_id: str) -> OperationalHealthSnapshot:
        report = self.inventory()
        return history.record(
            project_id,
            "backend",
            all(bool(item["healthy"]) for item in report.backends),
            report.model_dump(mode="json", exclude={"health_history"}),
        )


class OperationalDiagnosticsReport(BaseModel):
    """Composite operational report with JSON/Markdown transport helpers."""

    configuration: RuntimeConfigurationReport
    providers: ProviderInventoryReport
    backends: BackendInventoryReport
    dependencies: dict[str, bool] = Field(default_factory=dict)
    runtime_summary: dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _markdown("Operational Diagnostics", self.model_dump(mode="json"))


class OperationalDiagnostics:
    """Compose configuration, inventory, compatibility, and dependency diagnostics."""

    def __init__(
        self,
        *,
        configuration: RuntimeConfiguration,
        providers: ProviderManagement,
        backends: BackendManagement,
        dependencies: Mapping[str, bool] | None = None,
        history: HealthHistoryStore | None = None,
    ) -> None:
        self._configuration = configuration
        self._providers = providers
        self._backends = backends
        self._dependencies = dict(dependencies or {})
        self._history = history

    def report(self, project_id: str | None = None) -> OperationalDiagnosticsReport:
        configuration = self._configuration.report()
        providers = self._providers.inventory(history=self._history, project_id=project_id)
        backends = self._backends.inventory(history=self._history, project_id=project_id)
        runtime_healthy = (
            configuration.governance.compatible
            and configuration.governance.integrity_valid
            and providers.recommendation.available
            and all(bool(item["healthy"]) for item in backends.backends)
            and all(self._dependencies.values())
        )
        return OperationalDiagnosticsReport(
            configuration=configuration,
            providers=providers,
            backends=backends,
            dependencies=dict(sorted(self._dependencies.items())),
            runtime_summary={"healthy": runtime_healthy, "mode": "local", "network_probes": False},
        )


def _markdown(title: str, values: dict[str, Any]) -> str:
    lines = [f"# {title}", ""]
    for key, value in values.items():
        lines.extend([f"## {key.replace('_', ' ').title()}", "", "```json"])
        lines.append(json.dumps(value, indent=2, default=str))
        lines.extend(["```", ""])
    return "\n".join(lines)
