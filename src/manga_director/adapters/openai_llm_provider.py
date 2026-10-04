"""OpenAI LLM API boundary; network communication is intentionally absent."""

from manga_director.adapters._stub_llm_provider import StubLLMProvider


class OpenAILLMProvider(StubLLMProvider):
    provider_name = "openai"
