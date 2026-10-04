"""Compose a local runtime summary for operational diagnosis."""

from manga_director.adapters import ImageBackendRuntime, LLMProviderRuntime
from manga_director.cli.config import AppConfig
from manga_director.production import (
    BackendManagement,
    OperationalDiagnostics,
    ProviderManagement,
    RuntimeConfiguration,
)


def main() -> None:
    report = OperationalDiagnostics(
        configuration=RuntimeConfiguration(AppConfig()),
        providers=ProviderManagement(LLMProviderRuntime()),
        backends=BackendManagement(ImageBackendRuntime()),
        dependencies={"repository": True},
    ).report()
    print(report.to_markdown())


if __name__ == "__main__":
    main()
