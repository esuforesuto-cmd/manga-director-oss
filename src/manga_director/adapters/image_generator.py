from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field


class ImageResult(BaseModel):
    """Provider-neutral result returned by every image generator adapter."""

    model_config = ConfigDict(frozen=True)

    success: bool
    image_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    provider: str
    elapsed_time: float = Field(ge=0)
    messages: list[str] = Field(default_factory=list)


class ImageGenerator(Protocol):
    """The complete public image-provider boundary."""

    def generate(self, prompt: str) -> ImageResult: ...
