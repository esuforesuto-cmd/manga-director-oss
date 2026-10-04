"""Transport-neutral enterprise runtime diagnostics."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field

from manga_director.adapters.runtime import ImageBackendRuntime, LLMProviderRuntime
from manga_director.observability.health import HealthMonitor
from manga_director.observability.performance import PerformanceMonitor
from manga_director.repositories.scalability import RepositoryScalability


class EnterpriseDiagnosticsReport(BaseModel):
    """Safe high-level summary for operations, CLI, and future transports."""

    system_summary: dict[str, Any] = Field(default_factory=dict)
    repository_summary: dict[str, Any] = Field(default_factory=dict)
    provider_summary: dict[str, Any] = Field(default_factory=dict)
    backend_summary: dict[str, Any] = Field(default_factory=dict)
    configuration_summary: dict[str, Any] = Field(default_factory=dict)
    performance_summary: dict[str, Any] = Field(default_factory=dict)
    health_summary: dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        sections = (
            ("System", self.system_summary),
            ("Repository", self.repository_summary),
            ("Provider", self.provider_summary),
            ("Backend", self.backend_summary),
            ("Configuration", self.configuration_summary),
            ("Performance", self.performance_summary),
            ("Health", self.health_summary),
        )
        lines = ["# Enterprise Diagnostics", ""]
        for title, values in sections:
            lines.extend([f"## {title}", "", "```json", json.dumps(values, indent=2, default=str), "```", ""])
        return "\n".join(lines)


class EnterpriseDiagnostics:
    """Compose optional diagnostics without changing workflow control flow."""

    def __init__(
        self,
        *,
        config: object,
        providers: LLMProviderRuntime | None = None,
        backends: ImageBackendRuntime | None = None,
        repository: RepositoryScalability | None = None,
        performance: PerformanceMonitor | None = None,
        health: HealthMonitor | None = None,
        configuration_summary: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self._config = config
        self._providers = providers
        self._backends = backends
        self._repository = repository
        self._performance = performance
        self._health = health
        self._configuration_summary = configuration_summary or (
            lambda: {
                "profile": str(getattr(config, "profile", "unknown")),
                "read_only": bool(getattr(config, "read_only", False)),
            }
        )

    def report(self, project_id: str | None = None) -> EnterpriseDiagnosticsReport:
        repository_summary: dict[str, Any] = {}
        if self._repository is not None and project_id is not None:
            repository_summary = self._repository.scan(project_id).model_dump()
        provider_summary = self._providers.report().model_dump() if self._providers else {}
        backend_summary = self._backends.report().model_dump() if self._backends else {}
        health_summary = self._health.dashboard().model_dump() if self._health else {}
        return EnterpriseDiagnosticsReport(
            system_summary={
                "profile": str(getattr(self._config, "profile", "unknown")),
                "read_only": bool(getattr(self._config, "read_only", False)),
            },
            repository_summary=repository_summary,
            provider_summary=provider_summary,
            backend_summary=backend_summary,
            configuration_summary=self._configuration_summary(),
            performance_summary=self._performance.summary() if self._performance else {},
            health_summary=health_summary,
        )
