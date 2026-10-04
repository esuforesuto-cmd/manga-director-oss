"""LiteLLM API boundary; network communication is intentionally absent."""

from manga_director.adapters._stub_llm_provider import StubLLMProvider


class LiteLLMProvider(StubLLMProvider):
    provider_name = "litellm"
