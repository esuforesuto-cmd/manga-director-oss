"""Start and stop the optional production runtime with local mock boundaries."""

from manga_director.adapters import ImageBackendRuntime, LLMProviderRuntime
from manga_director.cli.config import AppConfig, configuration_governance
from manga_director.observability import RuntimeHealth
from manga_director.production import ProductionRuntime
from manga_director.repositories import InMemoryRepository, RepositorySelfCheck


def main() -> None:
    repository = InMemoryRepository()
    providers = LLMProviderRuntime()
    backends = ImageBackendRuntime()
    runtime = ProductionRuntime(
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
        dependencies={"repository": lambda: True},
    )
    print(runtime.start().to_json())
    print(runtime.shutdown().model_dump_json(indent=2))


if __name__ == "__main__":
    main()
