from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class EventType(StrEnum):
    PAGE_DESIGNED = "PageDesigned"
    PAGE_REVIEWED = "PageReviewed"
    STORYBOARD_CREATED = "StoryboardCreated"
    PROMPT_BUILT = "PromptBuilt"
    IMAGE_GENERATED = "ImageGenerated"
    QUALITY_PASSED = "QualityPassed"
    QUALITY_FAILED = "QualityFailed"
    PAGE_APPROVED = "PageApproved"
    PROJECT_STARTED = "ProjectStarted"
    PROJECT_COMPLETED = "ProjectCompleted"
    CHAPTER_STARTED = "ChapterStarted"
    CHAPTER_COMPLETED = "ChapterCompleted"
    BATCH_STARTED = "BatchStarted"
    BATCH_COMPLETED = "BatchCompleted"
    BATCH_PAUSED = "BatchPaused"
    BATCH_RESUMED = "BatchResumed"
    BATCH_FAILED = "BatchFailed"


class WorkflowEvent(BaseModel):
    """An immutable event emitted for an accepted workflow step."""

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType | str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data: dict[str, Any] = Field(default_factory=dict)
