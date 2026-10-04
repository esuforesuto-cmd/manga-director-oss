"""Build a complete local health report without executing workflow work."""

from manga_director.adapters import ImageBackendRuntime, LLMProviderRuntime
from manga_director.cli.config import AppConfig
from manga_director.observability import RuntimeHealth
from manga_director.repositories import InMemoryRepository, RepositorySelfCheck

print(
    RuntimeHealth(
        config=AppConfig(),
        providers=LLMProviderRuntime(),
        backends=ImageBackendRuntime(),
        repository_check=RepositorySelfCheck(InMemoryRepository()),
    ).report().to_markdown()
)
