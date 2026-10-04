"""Composite operational diagnostics timing with local mock boundaries."""

from __future__ import annotations

from time import perf_counter

from manga_director.adapters import ImageBackendRuntime, LLMProviderRuntime
from manga_director.cli.config import AppConfig
from manga_director.production import (
    BackendManagement,
    OperationalDiagnostics,
    ProviderManagement,
    RuntimeConfiguration,
)


def run() -> float:
    diagnostics = OperationalDiagnostics(
        configuration=RuntimeConfiguration(AppConfig()),
        providers=ProviderManagement(LLMProviderRuntime()),
        backends=BackendManagement(ImageBackendRuntime()),
        dependencies={"repository": True},
    )
    started = perf_counter()
    assert diagnostics.report().runtime_summary["healthy"] is True
    return perf_counter() - started
