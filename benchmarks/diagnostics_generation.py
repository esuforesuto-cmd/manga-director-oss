"""Reliability diagnostics DTO generation timing."""

from __future__ import annotations

from time import perf_counter

from manga_director.adapters import ImageBackendRuntime, LLMProviderRuntime
from manga_director.cli.config import AppConfig
from manga_director.observability import MetricsRegistry, RuntimeDiagnostics
from manga_director.production import (
    BackendManagement,
    ProviderManagement,
    ReliabilityDiagnostics,
    RuntimeConfiguration,
)


def run() -> float:
    diagnostics = ReliabilityDiagnostics(
        runtime=RuntimeDiagnostics(MetricsRegistry()),
        configuration=RuntimeConfiguration(AppConfig()),
        providers=ProviderManagement(LLMProviderRuntime()),
        backends=BackendManagement(ImageBackendRuntime()),
    )
    started = perf_counter()
    assert diagnostics.report().architecture["core_modified"] is False
    return perf_counter() - started
