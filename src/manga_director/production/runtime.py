"""Production lifecycle orchestration outside Core workflow responsibilities."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from time import perf_counter
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from manga_director.adapters.runtime import ImageBackendRuntime, LLMProviderRuntime
from manga_director.observability.metrics import MetricsRegistry
from manga_director.observability.runtime_health import RuntimeHealth, RuntimeHealthReport


class DependencyCheck(BaseModel):
    """Safe evidence for a startup dependency probe."""

    model_config = ConfigDict(frozen=True)

    name: str
    healthy: bool
    messages: tuple[str, ...] = ()


class StartupReport(BaseModel):
    """Transport-neutral startup result; no workflow state is changed."""

    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    ready: bool
    configuration: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[DependencyCheck] = Field(default_factory=list)
    provider_warmup: dict[str, Any] = Field(default_factory=dict)
    backend_warmup: dict[str, Any] = Field(default_factory=dict)
    elapsed_seconds: float = Field(ge=0)
    messages: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _render_markdown("Startup Report", self.model_dump(mode="json"))


class ShutdownReport(BaseModel):
    """Graceful shutdown evidence collected without raising from cleanup paths."""

    stopped_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    graceful: bool
    completed: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    elapsed_seconds: float = Field(ge=0)


class ProductionMetricsReport(BaseModel):
    """Stable, presentation-independent categories over in-process metrics."""

    startup: dict[str, Any] = Field(default_factory=dict)
    runtime: dict[str, Any] = Field(default_factory=dict)
    workflow: dict[str, Any] = Field(default_factory=dict)
    repository: dict[str, Any] = Field(default_factory=dict)
    provider: dict[str, Any] = Field(default_factory=dict)
    backend: dict[str, Any] = Field(default_factory=dict)
    automation: dict[str, Any] = Field(default_factory=dict)
    notification: dict[str, Any] = Field(default_factory=dict)
    performance: dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _render_markdown("Production Metrics", self.model_dump(mode="json"))


class ProductionHealthReport(BaseModel):
    """Readiness/liveness report that composes existing health DTOs safely."""

    live: bool
    ready: bool
    application: RuntimeHealthReport
    database: DependencyCheck
    system: dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _render_markdown("Production Health", self.model_dump(mode="json"))


class ProductionRuntimeReport(BaseModel):
    """Consolidated startup/runtime/dependency/provider/backend configuration DTO."""

    startup: StartupReport | None = None
    metrics: ProductionMetricsReport
    dependencies: list[DependencyCheck] = Field(default_factory=list)
    provider: dict[str, Any] = Field(default_factory=dict)
    backend: dict[str, Any] = Field(default_factory=dict)
    configuration: dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        return _render_markdown("Production Runtime Report", self.model_dump(mode="json"))


class ProductionMetrics:
    """Categorize existing metric names without an exporter or presentation dependency."""

    _categories = (
        "startup",
        "runtime",
        "workflow",
        "repository",
        "provider",
        "backend",
        "automation",
        "notification",
    )

    def __init__(self, registry: MetricsRegistry | None = None) -> None:
        self.registry = registry or MetricsRegistry()

    def report(self) -> ProductionMetricsReport:
        snapshot = self.registry.snapshot()
        counters = snapshot["counters"]
        durations = snapshot["durations"]
        if not isinstance(counters, dict) or not isinstance(durations, dict):
            raise RuntimeError("MetricsRegistry returned an invalid snapshot.")
        categories = {
            category: _metric_category(category, counters, durations) for category in self._categories
        }
        performance = {"durations": durations}
        return ProductionMetricsReport(**categories, performance=performance)


class ProductionRuntime:
    """Coordinates startup/shutdown probes; it never executes page workflow work."""

    def __init__(
        self,
        *,
        providers: LLMProviderRuntime,
        backends: ImageBackendRuntime,
        health: RuntimeHealth,
        configuration: Callable[[], Mapping[str, object]],
        dependencies: Mapping[str, Callable[[], bool]] | None = None,
        shutdown_hooks: Mapping[str, Callable[[], None]] | None = None,
        metrics: ProductionMetrics | None = None,
    ) -> None:
        self._providers = providers
        self._backends = backends
        self._health = health
        self._configuration = configuration
        self._dependencies = dict(dependencies or {})
        self._shutdown_hooks = dict(shutdown_hooks or {})
        self._metrics = metrics or ProductionMetrics()
        self._startup: StartupReport | None = None

    def start(self) -> StartupReport:
        """Validate boundaries and warm local adapters without network or workflow calls."""

        if self._startup is not None:
            return self._startup
        started = perf_counter()
        configuration = dict(_safe_mapping(self._configuration))
        dependencies = self._dependency_report()
        provider_warmup = self._providers.warmup().model_dump(mode="json")
        backend_warmup = self._backends.warmup().model_dump(mode="json")
        ready = (
            bool(configuration.get("compatible", False))
            and bool(configuration.get("integrity_valid", False))
            and all(item.healthy for item in dependencies)
            and bool(provider_warmup["ready"])
            and bool(backend_warmup["ready"])
        )
        self._metrics.registry.increment("startup.attempts")
        self._metrics.registry.increment("startup.ready" if ready else "startup.failed")
        self._metrics.registry.observe("startup.duration_seconds", perf_counter() - started)
        self._startup = StartupReport(
            ready=ready,
            configuration=configuration,
            dependencies=dependencies,
            provider_warmup=provider_warmup,
            backend_warmup=backend_warmup,
            elapsed_seconds=perf_counter() - started,
            messages=[] if ready else ["Startup validation did not reach readiness."],
        )
        return self._startup

    def readiness(self) -> bool:
        return self.start().ready

    def liveness(self) -> bool:
        """Liveness is process-local and does not make external requests."""

        return True

    def health_report(self, project_id: str | None = None) -> ProductionHealthReport:
        application = self._health.report(project_id)
        database = next(
            (item for item in self._dependency_report() if item.name == "database"),
            DependencyCheck(name="database", healthy=True, messages=("not_configured",)),
        )
        return ProductionHealthReport(
            live=self.liveness(),
            ready=self.readiness() and application.healthy and database.healthy,
            application=application,
            database=database,
            system={"mode": "local", "network_probes": False},
        )

    def report(self) -> ProductionRuntimeReport:
        startup = self._startup
        return ProductionRuntimeReport(
            startup=startup,
            metrics=self._metrics.report(),
            dependencies=self._dependency_report(),
            provider=self._providers.report().model_dump(mode="json"),
            backend=self._backends.report().model_dump(mode="json"),
            configuration=dict(_safe_mapping(self._configuration)),
        )

    def shutdown(self) -> ShutdownReport:
        """Run hooks then close adapter lifecycle handles, retaining every cleanup error."""

        started = perf_counter()
        completed: list[str] = []
        errors: list[str] = []
        for name, hook in reversed(tuple(self._shutdown_hooks.items())):
            try:
                hook()
            except Exception as exc:
                errors.append(f"{name}: {exc}")
            else:
                completed.append(name)
        for name, runtime in (("backends", self._backends), ("providers", self._providers)):
            try:
                runtime.shutdown()
            except Exception as exc:
                errors.append(f"{name}: {exc}")
            else:
                completed.append(name)
        self._metrics.registry.increment("runtime.shutdowns")
        self._metrics.registry.observe("runtime.shutdown.duration_seconds", perf_counter() - started)
        return ShutdownReport(
            graceful=not errors,
            completed=tuple(completed),
            errors=tuple(errors),
            elapsed_seconds=perf_counter() - started,
        )

    def _dependency_report(self) -> list[DependencyCheck]:
        return [
            DependencyCheck(name=name, healthy=_safe_check(check))
            for name, check in sorted(self._dependencies.items())
        ]


def _metric_category(
    category: str, counters: dict[str, object], durations: dict[str, object]
) -> dict[str, Any]:
    prefix = f"{category}."
    return {
        "counters": {key: value for key, value in counters.items() if key.startswith(prefix)},
        "durations": {key: value for key, value in durations.items() if key.startswith(prefix)},
    }


def _safe_check(check: Callable[[], bool]) -> bool:
    try:
        return bool(check())
    except Exception:
        return False


def _safe_mapping(provider: Callable[[], Mapping[str, object]]) -> Mapping[str, object]:
    try:
        return provider()
    except Exception:
        return {"compatible": False, "integrity_valid": False, "available": False}


def _render_markdown(title: str, values: dict[str, Any]) -> str:
    lines = [f"# {title}", ""]
    for key, value in values.items():
        lines.extend([f"## {key.replace('_', ' ').title()}", "", "```json"])
        lines.append(json.dumps(value, indent=2, default=str))
        lines.extend(["```", ""])
    return "\n".join(lines)
