"""Passive runtime diagnostics for plugin, extension, and configuration boundaries."""

from __future__ import annotations

import platform
import sys
from collections.abc import Mapping

from pydantic import BaseModel, Field

from manga_director.observability.metrics import MetricsRegistry
from manga_director.observability.performance import PerformanceMonitor


class RuntimeDiagnosticReport(BaseModel):
    """Safe operational data collected without changing runtime control flow."""

    system: dict[str, object] = Field(default_factory=dict)
    plugins: dict[str, object] = Field(default_factory=dict)
    extensions: dict[str, object] = Field(default_factory=dict)
    configuration: dict[str, object] = Field(default_factory=dict)
    repositories: dict[str, object] = Field(default_factory=dict)
    providers: dict[str, object] = Field(default_factory=dict)
    backends: dict[str, object] = Field(default_factory=dict)
    workflow: dict[str, object] = Field(default_factory=dict)
    events: dict[str, object] = Field(default_factory=dict)
    performance: dict[str, object] = Field(default_factory=dict)

    def to_json(self) -> str:
        """Render the DTO as transport-neutral JSON without exposing internal objects."""

        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        """Render a concise operational report without a presentation-layer dependency."""

        sections = [
            ("System", self.system),
            ("Performance", self.performance),
            ("Configuration", self.configuration),
            ("Plugins", self.plugins),
            ("Extensions", self.extensions),
            ("Repositories", self.repositories),
            ("Providers", self.providers),
            ("Backends", self.backends),
            ("Workflow", self.workflow),
            ("Events", self.events),
        ]
        lines = ["# manga-director Runtime Diagnostics", ""]
        for title, data in sections:
            lines.extend([f"## {title}", ""])
            if data:
                lines.extend(f"- `{key}`: `{value}`" for key, value in sorted(data.items()))
            else:
                lines.append("- No data configured.")
            lines.append("")
        return "\n".join(lines)


class RuntimeDiagnostics:
    """Compose safe snapshots supplied by runtime boundaries and existing metrics."""

    def __init__(
        self,
        metrics: MetricsRegistry,
        performance: PerformanceMonitor | None = None,
    ) -> None:
        self._metrics = metrics
        self._performance = performance or PerformanceMonitor(metrics)

    def report(
        self,
        *,
        plugins: Mapping[str, object] | None = None,
        extensions: Mapping[str, object] | None = None,
        configuration: Mapping[str, object] | None = None,
        repositories: Mapping[str, object] | None = None,
        providers: Mapping[str, object] | None = None,
        backends: Mapping[str, object] | None = None,
        workflow: Mapping[str, object] | None = None,
        events: Mapping[str, object] | None = None,
    ) -> RuntimeDiagnosticReport:
        """Build a report from supplied safe snapshots; no service is invoked here."""

        return RuntimeDiagnosticReport(
            system={
                "python_version": platform.python_version(),
                "implementation": platform.python_implementation(),
                "platform": sys.platform,
            },
            plugins=dict(plugins or {}),
            extensions=dict(extensions or {}),
            configuration=dict(configuration or {}),
            repositories=dict(repositories or {}),
            providers=dict(providers or {}),
            backends=dict(backends or {}),
            workflow=dict(workflow or {}),
            events=dict(events or {}),
            performance=self._performance.summary(),
        )
