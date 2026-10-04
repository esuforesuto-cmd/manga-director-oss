"""Google Gemini LLM API boundary; network communication is intentionally absent."""

from manga_director.adapters._stub_llm_provider import StubLLMProvider


class GeminiLLMProvider(StubLLMProvider):
    provider_name = "gemini"
