"""Provider-neutral LLM contracts."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class PromptRequest(BaseModel):
    """A complete prompt request accepted by every LLM provider."""

    model_config = ConfigDict(frozen=True)

    system_prompt: str = ""
    user_prompt: str
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    max_tokens: int = Field(default=512, gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PromptResponse(BaseModel):
    """Normalized content returned by an LLM before provider execution metadata."""

    model_config = ConfigDict(frozen=True)

    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    messages: list[str] = Field(default_factory=list)


class LLMResult(BaseModel):
    """Provider-neutral result returned by every LLM adapter."""

    model_config = ConfigDict(frozen=True)

    success: bool
    content: str = ""
    usage: dict[str, int] = Field(default_factory=dict)
    provider: str
    elapsed_time: float = Field(ge=0.0)
    finish_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    messages: list[str] = Field(default_factory=list)

    @property
    def response(self) -> PromptResponse:
        """Expose normalized prompt content without weakening the result contract."""
        return PromptResponse(content=self.content, metadata=self.metadata, messages=self.messages)


@runtime_checkable
class LLMProvider(Protocol):
    """The complete public LLM-provider boundary."""

    def generate(self, request: PromptRequest) -> LLMResult: ...
