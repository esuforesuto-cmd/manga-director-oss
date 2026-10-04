"""Compose a local application health report without an HTTP server."""

from manga_director.adapters import ImageBackendRuntime, LLMProviderRuntime
from manga_director.cli.config import AppConfig, configuration_governance
from manga_director.observability import RuntimeHealth
from manga_director.repositories import InMemoryRepository, RepositorySelfCheck


def main() -> None:
    repository = InMemoryRepository()
    report = RuntimeHealth(
        config=AppConfig(),
        providers=LLMProviderRuntime(),
        backends=ImageBackendRuntime(),
        repository_check=RepositorySelfCheck(repository),
        configuration_summary=lambda: configuration_governance(AppConfig()).model_dump(),
    ).report()
    print(report.to_markdown())


if __name__ == "__main__":
    main()
