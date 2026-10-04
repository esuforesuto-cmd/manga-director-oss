"""Application-layer health summaries for optional runtime boundaries."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from manga_director.adapters.runtime import ImageBackendRuntime, LLMProviderRuntime
from manga_director.repositories.integrity import RepositorySelfCheck


class AdapterHealthSummary(BaseModel):
    """Safe aggregate health for a provider or image-backend registry."""

    kind: str
    registered: int = Field(ge=0)
    healthy: int = Field(ge=0)
    unavailable: int = Field(ge=0)
    states: dict[str, int] = Field(default_factory=dict)
    messages: dict[str, list[str]] = Field(default_factory=dict)


class RuntimeHealthReport(BaseModel):
    """Presentation-independent operational health DTO."""

    healthy: bool
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    provider: AdapterHealthSummary
    backend: AdapterHealthSummary
    repository: dict[str, Any] = Field(default_factory=dict)
    workflow: dict[str, Any] = Field(default_factory=dict)
    configuration: dict[str, Any] = Field(default_factory=dict)
    plugins: dict[str, Any] = Field(default_factory=dict)
    extensions: dict[str, Any] = Field(default_factory=dict)
    system: dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        lines = ["# Runtime Health", "", f"Overall healthy: `{self.healthy}`", ""]
        for title, value in (
            ("Provider", self.provider.model_dump()),
            ("Backend", self.backend.model_dump()),
            ("Repository", self.repository),
            ("Workflow", self.workflow),
            ("Configuration", self.configuration),
            ("Plugins", self.plugins),
            ("Extensions", self.extensions),
            ("System", self.system),
        ):
            lines.extend([f"## {title}", ""])
            lines.extend(f"- `{key}`: `{item}`" for key, item in sorted(value.items()))
            lines.append("")
        return "\n".join(lines)


class RuntimeHealth:
    """Collect isolated health evidence without steering workflow execution."""

    def __init__(
        self,
        *,
        config: object,
        providers: LLMProviderRuntime,
        backends: ImageBackendRuntime,
        repository_check: RepositorySelfCheck,
        workflow_check: Callable[[], bool] | None = None,
        plugin_check: Callable[[], bool] | None = None,
        extension_check: Callable[[], bool] | None = None,
        plugin_details: Callable[[], Mapping[str, object]] | None = None,
        extension_details: Callable[[], Mapping[str, object]] | None = None,
        configuration_summary: Callable[[], Mapping[str, object]] | None = None,
    ) -> None:
        self._config = config
        self._providers = providers
        self._backends = backends
        self._repository_check = repository_check
        self._workflow_check = workflow_check or (lambda: True)
        self._plugin_check = plugin_check or (lambda: True)
        self._extension_check = extension_check or (lambda: True)
        self._plugin_details = plugin_details or (lambda: {})
        self._extension_details = extension_details or (lambda: {})
        self._configuration_summary = configuration_summary or (
            lambda: {
                "profile": str(getattr(config, "profile", "unknown")),
                "read_only": bool(getattr(config, "read_only", False)),
                "compatible": True,
                "integrity_valid": True,
            }
        )

    def report(self, project_id: str | None = None) -> RuntimeHealthReport:
        provider = _adapter_summary("provider", self._providers)
        backend = _adapter_summary("backend", self._backends)
        repository = self._repository_check.check(project_id).model_dump()
        workflow_healthy = _safe(self._workflow_check)
        plugins_healthy = _safe(self._plugin_check)
        extensions_healthy = _safe(self._extension_check)
        configuration = dict(_safe_details(self._configuration_summary))
        configuration["healthy"] = bool(configuration.get("compatible", False)) and bool(
            configuration.get("integrity_valid", False)
        )
        plugins = {"healthy": plugins_healthy, **dict(_safe_details(self._plugin_details))}
        extensions = {"healthy": extensions_healthy, **dict(_safe_details(self._extension_details))}
        workflow = {"healthy": workflow_healthy, "scope": "one_page"}
        healthy = all(
            (
                provider.unavailable == 0,
                backend.unavailable == 0,
                bool(repository["healthy"]),
                workflow_healthy,
                bool(configuration["healthy"]),
                plugins_healthy,
                extensions_healthy,
            )
        )
        return RuntimeHealthReport(
            healthy=healthy,
            provider=provider,
            backend=backend,
            repository=repository,
            workflow=workflow,
            configuration=configuration,
            plugins=plugins,
            extensions=extensions,
            system={"mode": "local", "network_probes": False},
        )


def _adapter_summary(kind: str, runtime: LLMProviderRuntime | ImageBackendRuntime) -> AdapterHealthSummary:
    snapshots = runtime.health_snapshot()
    unavailable = sum(item.state == "unavailable" for item in snapshots)
    return AdapterHealthSummary(
        kind=kind,
        registered=len(snapshots),
        healthy=sum(item.state == "healthy" for item in snapshots),
        unavailable=unavailable,
        states=runtime.lifecycle().summary(),
        messages={item.name: list(item.messages) for item in snapshots if item.messages},
    )


def _safe(check: Callable[[], bool]) -> bool:
    try:
        return bool(check())
    except Exception:
        return False


def _safe_details(provider: Callable[[], Mapping[str, object]]) -> Mapping[str, object]:
    try:
        return provider()
    except Exception:
        return {"available": False}
