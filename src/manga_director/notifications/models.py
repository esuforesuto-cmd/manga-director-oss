from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class NotificationMessage(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str
    title: str
    body: str
    severity: str = "INFO"
    project_id: str | None = None
    chapter_id: str | None = None
    page_number: int | None = None
    trace_id: str | None = None
    correlation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NotificationResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    success: bool
    provider: str
    message_id: str
    status_code: int | None = None
    attempts: int = 1
    elapsed_time: float = 0.0
    messages: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
