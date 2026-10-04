"""Passive discovery and diagnostics for registered AI and image adapters."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from time import perf_counter
from typing import Any

from pydantic import BaseModel, Field

from manga_director.adapters.factory import ImageGeneratorFactory
from manga_director.adapters.lifecycle import AdapterLifecycle, AdapterLifecycleSnapshot
from manga_director.adapters.llm_factory import LLMFactory
from manga_director.adapters.runtime_models import (
    AdapterHealth,
    AdapterMetadata,
    AdapterWarmupReport,
    ProviderFallbackPolicy,
)


class AdapterRuntimeReport(BaseModel):
    """Transport-neutral discovery, capability, model, and health report."""

    kind: str
    summary: dict[str, int] = Field(default_factory=dict)
    providers: list[AdapterMetadata] = Field(default_factory=list)
    health: list[AdapterHealth] = Field(default_factory=list)
    models: dict[str, list[str]] = Field(default_factory=dict)
    capabilities: dict[str, list[str]] = Field(default_factory=dict)
    presets: dict[str, list[str]] = Field(default_factory=dict)

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    def to_markdown(self) -> str:
        lines = [f"# {self.kind.title()} Runtime Report", "", "## Summary", ""]
        lines.extend(f"- `{key}`: `{value}`" for key, value in sorted(self.summary.items()))
        lines.extend(["", "## Registered adapters", ""])
        for item in self.providers:
            status = next((health.healthy for health in self.health if health.name == item.name), False)
            lines.append(f"- `{item.name}`: priority `{item.priority}`, healthy `{status}`")
        return "\n".join(lines)


class _AdapterRuntime:
    """Shared passive runtime logic; it never invokes adapter generate methods."""

    kind: str

    def __init__(
        self,
        metadata: Callable[[], list[AdapterMetadata]],
        create: Callable[[str], Any],
        resolve: Callable[[str], str],
    ) -> None:
        self._metadata = metadata
        self._create = create
        self._resolve = resolve
        self._discovery_cache: tuple[AdapterMetadata, ...] | None = None

    def discover(self, *, refresh: bool = False) -> list[AdapterMetadata]:
        """Discover registered adapters with a small, explicitly refreshable cache."""

        if refresh or self._discovery_cache is None:
            self._discovery_cache = tuple(self._metadata())
        return list(self._discovery_cache)

    def invalidate_cache(self) -> None:
        self._discovery_cache = None

    def refresh_metadata(self) -> list[AdapterMetadata]:
        """Refresh registry metadata explicitly after a controlled registry update."""

        return self.discover(refresh=True)

    def refresh_capabilities(self) -> dict[str, list[str]]:
        """Refresh metadata, then return the current capability index."""

        self.refresh_metadata()
        return self.capability_report()

    def evaluate_priority(self) -> list[str]:
        """Return deterministic preference order; selection/fallback stays declarative."""

        return [item.name for item in self.discover()]

    def priority_inventory(self, overrides: Mapping[str, int] | None = None) -> list[AdapterMetadata]:
        """Return a diagnostic priority plan without changing factory registrations."""

        requested = overrides or {}
        return sorted(
            self.discover(),
            key=lambda item: (requested.get(item.name, item.priority), item.name),
        )

    def inventory(self, *, refresh: bool = False) -> AdapterRuntimeReport:
        """Return a safe inventory, optionally after an explicit metadata refresh."""

        if refresh:
            self.refresh_metadata()
        return self.report()

    def resolve(self, name_or_alias: str) -> str:
        return self._resolve(name_or_alias)

    def capability_report(self) -> dict[str, list[str]]:
        capabilities: defaultdict[str, list[str]] = defaultdict(list)
        for metadata in self.discover():
            for capability in metadata.capabilities:
                capabilities[capability].append(metadata.name)
        return {key: sorted(value) for key, value in sorted(capabilities.items())}

    def model_report(self) -> dict[str, list[str]]:
        return {metadata.name: list(metadata.models) for metadata in self.discover()}

    def preset_report(self) -> dict[str, list[str]]:
        return {metadata.name: sorted(metadata.presets) for metadata in self.discover()}

    def health(self) -> list[AdapterHealth]:
        """Check local construction only; network health stays adapter-specific and future work."""

        checks: list[AdapterHealth] = []
        for metadata in self.discover():
            try:
                self._create(metadata.name)
            except Exception as exc:
                checks.append(AdapterHealth(name=metadata.name, healthy=False, messages=[str(exc)]))
            else:
                checks.append(AdapterHealth(name=metadata.name, healthy=True))
        return checks

    def report(self) -> AdapterRuntimeReport:
        providers = self.discover()
        health = self.health()
        return AdapterRuntimeReport(
            kind=self.kind,
            summary={"registered": len(providers), "healthy": sum(item.healthy for item in health)},
            providers=providers,
            health=health,
            models=self.model_report(),
            capabilities=self.capability_report(),
            presets=self.preset_report(),
        )


class LLMProviderRuntime(_AdapterRuntime):
    """Discovery and diagnostics facade for registered LLM providers."""

    kind = "provider"

    def __init__(self) -> None:
        super().__init__(LLMFactory.metadata, LLMFactory.create, LLMFactory.resolve)
        self._lifecycle = AdapterLifecycle(self.discover, self.health)

    def fallback_policy(self, providers: tuple[str, ...] = ()) -> ProviderFallbackPolicy:
        """Return a declarative policy; execution remains intentionally unimplemented."""

        return ProviderFallbackPolicy(providers=providers)

    def fallback_simulation(self, providers: tuple[str, ...] = ()) -> ProviderFallbackPolicy:
        """Expose planned fallback order without invoking or switching providers."""

        return self.fallback_policy(providers or tuple(self.evaluate_priority()))

    def warmup(self) -> AdapterWarmupReport:
        return _warmup(self)

    def lifecycle(self) -> AdapterLifecycle:
        return self._lifecycle

    def initialize(self) -> list[AdapterLifecycleSnapshot]:
        return self._lifecycle.initialize()

    def health_snapshot(self) -> list[AdapterLifecycleSnapshot]:
        return self._lifecycle.refresh_health()

    def shutdown(self) -> list[AdapterLifecycleSnapshot]:
        return self._lifecycle.shutdown()


class ImageBackendRuntime(_AdapterRuntime):
    """Discovery and diagnostics facade for registered image backends."""

    kind = "image backend"

    def __init__(self) -> None:
        super().__init__(ImageGeneratorFactory.metadata, ImageGeneratorFactory.create, ImageGeneratorFactory.resolve)
        self._lifecycle = AdapterLifecycle(self.discover, self.health)

    def lifecycle(self) -> AdapterLifecycle:
        return self._lifecycle

    def warmup(self) -> AdapterWarmupReport:
        return _warmup(self)

    def initialize(self) -> list[AdapterLifecycleSnapshot]:
        return self._lifecycle.initialize()

    def health_snapshot(self) -> list[AdapterLifecycleSnapshot]:
        return self._lifecycle.refresh_health()

    def shutdown(self) -> list[AdapterLifecycleSnapshot]:
        return self._lifecycle.shutdown()

    def validate_preset(self, backend: str, preset: str) -> dict[str, object]:
        """Validate a declared backend preset without executing a generator."""

        resolved = self.resolve(backend)
        metadata = next(item for item in self.discover() if item.name == resolved)
        try:
            return dict(metadata.presets[preset])
        except KeyError as exc:
            raise ValueError(f"Unknown preset '{preset}' for backend '{resolved}'.") from exc

    def validate_workflow(self, backend: str, workflow: dict[str, object]) -> bool:
        """Confirm that workflow metadata is supported by the declared backend."""

        resolved = self.resolve(backend)
        metadata = next(item for item in self.discover() if item.name == resolved)
        if not metadata.workflow_metadata:
            raise ValueError(f"Backend '{resolved}' does not declare workflow metadata.")
        required_format = metadata.workflow_metadata.get("format")
        if required_format is not None and workflow.get("format") != required_format:
            raise ValueError(f"Workflow format must be '{required_format}' for backend '{resolved}'.")
        return True

    def workflow_compatibility_report(
        self, backend: str, workflow: dict[str, object]
    ) -> dict[str, object]:
        """Return compatibility evidence rather than exposing a validation exception."""

        try:
            compatible = self.validate_workflow(backend, workflow)
        except ValueError as exc:
            return {"backend": backend, "compatible": False, "messages": [str(exc)]}
        return {"backend": self.resolve(backend), "compatible": compatible, "messages": []}


def _warmup(runtime: LLMProviderRuntime | ImageBackendRuntime) -> AdapterWarmupReport:
    """Prepare local lifecycle evidence without provider/backend execution."""

    started = perf_counter()
    runtime.initialize()
    snapshots = runtime.health_snapshot()
    healthy = sum(item.state.value == "healthy" for item in snapshots)
    return AdapterWarmupReport(
        kind=runtime.kind,
        ready=healthy == len(snapshots),
        registered=len(snapshots),
        healthy=healthy,
        elapsed_seconds=perf_counter() - started,
        messages=[message for item in snapshots for message in item.messages],
    )
