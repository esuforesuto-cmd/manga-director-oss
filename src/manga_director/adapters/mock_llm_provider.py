"""Deterministic LLM provider for tests and local development."""

from __future__ import annotations

from manga_director.adapters.llm_provider import LLMResult, PromptRequest


class MockLLM:
    """Returns a fixed response without network access."""

    def __init__(self, content: str = "Mock LLM response.") -> None:
        self._content = content

    def generate(self, request: PromptRequest) -> LLMResult:
        return LLMResult(
            success=True,
            content=self._content,
            usage={"input_tokens": 0, "output_tokens": 0},
            provider="mock",
            elapsed_time=0.0,
            finish_reason="stop",
            metadata={"request_metadata": request.metadata},
            messages=["Mock LLM response generated."],
        )
