"""Registry-backed LLM provider factory."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from manga_director.adapters.anthropic_llm_provider import AnthropicLLMProvider
from manga_director.adapters.gemini_llm_provider import GeminiLLMProvider
from manga_director.adapters.litellm_provider import LiteLLMProvider
from manga_director.adapters.llm_provider import LLMProvider
from manga_director.adapters.mock_llm_provider import MockLLM
from manga_director.adapters.ollama_llm_provider import OllamaLLMProvider
from manga_director.adapters.openai_llm_provider import OpenAILLMProvider
from manga_director.adapters.openrouter_llm_provider import OpenRouterLLMProvider
from manga_director.adapters.runtime_models import AdapterMetadata
from manga_director.domain.exceptions import ConfigurationError, LLMProviderError

LLMBuilder = Callable[..., LLMProvider]


class LLMFactory:
    """Creates registered providers without provider-specific branching."""

    _registry: dict[str, LLMBuilder] = {}
    _metadata: dict[str, AdapterMetadata] = {}

    @classmethod
    def register(
        cls, provider: str, builder: LLMBuilder, metadata: AdapterMetadata | None = None
    ) -> None:
        normalized = provider.strip().lower()
        if not normalized:
            raise ConfigurationError("LLM provider name is required.")
        cls._registry[normalized] = builder
        cls._metadata[normalized] = metadata or AdapterMetadata(
            name=normalized, display_name=normalized
        )

    @classmethod
    def create(cls, provider: str, **options: Any) -> LLMProvider:
        normalized = provider.strip().lower()
        try:
            builder = cls._registry[normalized]
        except KeyError as exc:
            raise LLMProviderError(f"Unsupported LLM provider: {provider}") from exc
        return builder(**options)

    @classmethod
    def available(cls) -> list[str]:
        return sorted(cls._registry)

    @classmethod
    def metadata(cls) -> list[AdapterMetadata]:
        """Return registered metadata in deterministic priority order."""

        return sorted(cls._metadata.values(), key=lambda item: (item.priority, item.name))

    @classmethod
    def resolve(cls, provider_or_alias: str) -> str:
        """Resolve a provider name, model name, or registered alias without creating it."""

        normalized = provider_or_alias.strip().lower()
        matches = [
            metadata
            for metadata in cls.metadata()
            if normalized == metadata.name
            or normalized in {alias.lower() for alias in metadata.aliases}
            or normalized in {model.lower() for model in metadata.models}
        ]
        if not matches:
            raise LLMProviderError(f"Unsupported LLM provider or alias: {provider_or_alias}")
        return matches[0].name


LLMFactory.register(
    "mock",
    MockLLM,
    AdapterMetadata(
        name="mock",
        display_name="Mock LLM",
        priority=0,
        capabilities=("text", "deterministic"),
        models=("mock-llm",),
        aliases={"default": "mock-llm", "offline": "mock-llm"},
    ),
)
LLMFactory.register(
    "openai",
    OpenAILLMProvider,
    AdapterMetadata(name="openai", display_name="OpenAI", capabilities=("text",)),
)
LLMFactory.register(
    "anthropic",
    AnthropicLLMProvider,
    AdapterMetadata(name="anthropic", display_name="Anthropic", capabilities=("text",)),
)
LLMFactory.register(
    "gemini",
    GeminiLLMProvider,
    AdapterMetadata(name="gemini", display_name="Google Gemini", capabilities=("text",)),
)
LLMFactory.register(
    "ollama",
    OllamaLLMProvider,
    AdapterMetadata(name="ollama", display_name="Ollama", capabilities=("text", "local")),
)
LLMFactory.register(
    "openrouter",
    OpenRouterLLMProvider,
    AdapterMetadata(name="openrouter", display_name="OpenRouter", capabilities=("text",)),
)
LLMFactory.register(
    "litellm",
    LiteLLMProvider,
    AdapterMetadata(name="litellm", display_name="LiteLLM", capabilities=("text",)),
)
