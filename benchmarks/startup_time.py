"""Provider-free startup timing for the application-layer production runtime."""

from __future__ import annotations

from time import perf_counter

from manga_director.adapters import ImageBackendRuntime, LLMProviderRuntime
from manga_director.cli.config import AppConfig, configuration_governance
from manga_director.observability import RuntimeHealth
from manga_director.production import ProductionRuntime
from manga_director.repositories import InMemoryRepository, RepositorySelfCheck


def build_runtime() -> ProductionRuntime:
    """Construct a production runtime with local mock-backed boundaries."""

    repository = InMemoryRepository()
    providers = LLMProviderRuntime()
    backends = ImageBackendRuntime()
    return ProductionRuntime(
        providers=providers,
        backends=backends,
        health=RuntimeHealth(
            config=AppConfig(),
            providers=providers,
            backends=backends,
            repository_check=RepositorySelfCheck(repository),
            configuration_summary=lambda: configuration_governance(AppConfig()).model_dump(),
        ),
        configuration=lambda: configuration_governance(AppConfig()).model_dump(),
    )
def run() -> float:
    """Return a local startup duration without accessing a network provider."""

    runtime = build_runtime()
    started = perf_counter()
    assert runtime.start().ready is True
    return perf_counter() - started
