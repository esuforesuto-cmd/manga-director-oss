"""Shared API-boundary stub for future network-backed LLM adapters."""

from __future__ import annotations

from manga_director.adapters.llm_provider import LLMResult, PromptRequest


class StubLLMProvider:
    """Returns an explicit unavailable result without making a network request."""

    provider_name = "stub"

    def generate(self, request: PromptRequest) -> LLMResult:
        # TODO: Resolve provider credentials at composition time.
        # TODO: Perform provider HTTP/API request and normalize usage metadata.
        # TODO: Apply timeout, retry, and safe response persistence policies.
        return LLMResult(
            success=False,
            content="",
            usage={},
            provider=self.provider_name,
            elapsed_time=0.0,
            finish_reason="not_implemented",
            metadata={"request_metadata": request.metadata},
            messages=[f"{self.provider_name} LLM provider is an API-boundary stub."],
        )
