"""Ollama LLM API boundary; network communication is intentionally absent."""

from manga_director.adapters._stub_llm_provider import StubLLMProvider


class OllamaLLMProvider(StubLLMProvider):
    provider_name = "ollama"
