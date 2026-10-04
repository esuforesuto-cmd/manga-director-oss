"""Typed contracts shared by independently replaceable prompt-pipeline stages."""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field


class PromptInput(BaseModel):
    """Normalized source artifacts consumed by the prompt builder."""

    model_config = ConfigDict(frozen=True)

    page_number: str
    page_design: dict[str, Any] = Field(default_factory=dict)
    storyboard: dict[str, Any] = Field(default_factory=dict)
    dialogue: list[str] = Field(default_factory=list)
    character: dict[str, Any] = Field(default_factory=dict)
    world: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class StructuredPrompt(BaseModel):
    """Provider-neutral prompt data before Markdown rendering."""

    model_config = ConfigDict(frozen=True)

    page_number: str
    page_design: dict[str, Any] = Field(default_factory=dict)
    panels: list[dict[str, Any]] = Field(default_factory=list)
    dialogue: list[str] = Field(default_factory=list)
    character: dict[str, Any] = Field(default_factory=dict)
    world: dict[str, Any] = Field(default_factory=dict)
    sections: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class PromptTemplate(BaseModel):
    """A Markdown template supplied by the package, a project, or a future plugin."""

    model_config = ConfigDict(frozen=True)

    name: str
    content: str
    source: str
    content_hash: str


class PromptValidation(BaseModel):
    """Non-fatal validation findings emitted by PromptValidator."""

    model_config = ConfigDict(frozen=True)

    warnings: list[str] = Field(default_factory=list)


class PromptResult(BaseModel):
    """The rendered, auditable result returned by a completed prompt pipeline."""

    model_config = ConfigDict(frozen=True)

    success: bool
    prompt: str = ""
    tokens: int = Field(default=0, ge=0)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    messages: list[str] = Field(default_factory=list)


class PromptBuilderPort(Protocol):
    def build(self, source: PromptInput) -> StructuredPrompt: ...


class PromptOptimizerPort(Protocol):
    def optimize(self, prompt: StructuredPrompt) -> StructuredPrompt: ...


class PromptValidatorPort(Protocol):
    def validate(self, prompt: StructuredPrompt, template: PromptTemplate) -> PromptValidation: ...


class PromptRendererPort(Protocol):
    def render(self, prompt: StructuredPrompt, template: PromptTemplate) -> PromptResult: ...


class PromptTemplateLoaderPort(Protocol):
    def load(self, name: str) -> PromptTemplate: ...
