"""Anthropic LLM API boundary; network communication is intentionally absent."""

from manga_director.adapters._stub_llm_provider import StubLLMProvider


class AnthropicLLMProvider(StubLLMProvider):
    provider_name = "anthropic"
