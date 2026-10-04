"""Render read-only architecture and runtime diagnostics."""

from manga_director.adapters import ImageBackendRuntime, LLMProviderRuntime
from manga_director.cli.config import AppConfig
from manga_director.observability import MetricsRegistry, RuntimeDiagnostics
from manga_director.production import (
    BackendManagement,
    ProviderManagement,
    ReliabilityDiagnostics,
    RuntimeConfiguration,
)


def main() -> None:
    report = ReliabilityDiagnostics(
        runtime=RuntimeDiagnostics(MetricsRegistry()),
        configuration=RuntimeConfiguration(AppConfig()),
        providers=ProviderManagement(LLMProviderRuntime()),
        backends=BackendManagement(ImageBackendRuntime()),
    ).report()
    print(report.to_markdown())


if __name__ == "__main__":
    main()
