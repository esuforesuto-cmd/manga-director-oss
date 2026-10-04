"""Typed contracts for persisted, sequential batch workflow orchestration."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from manga_director.domain.events import WorkflowEvent
from manga_director.workflow.contracts import WorkflowContext, WorkflowResult


class ExecutionPolicyName(StrEnum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    AUTO = "auto"


class BatchStatus(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETED = "completed"


class QueueItemStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class ExecutionPolicy:
    """Policy descriptor; only SequentialExecution is executable in this release."""

    name: ExecutionPolicyName
    executable: bool = False


@dataclass(frozen=True)
class SequentialExecution(ExecutionPolicy):
    name: ExecutionPolicyName = ExecutionPolicyName.SEQUENTIAL
    executable: bool = True


@dataclass(frozen=True)
class ParallelExecution(ExecutionPolicy):
    """API placeholder for a future isolated parallel worker implementation."""

    name: ExecutionPolicyName = ExecutionPolicyName.PARALLEL
    executable: bool = False


@dataclass(frozen=True)
class AutoExecution(ExecutionPolicy):
    """API placeholder for a future policy-selection strategy."""

    name: ExecutionPolicyName = ExecutionPolicyName.AUTO
    executable: bool = False


class QueueItem(BaseModel):
    """One persisted, page-scoped work item with explicit predecessor dependencies."""

    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    chapter_id: str = Field(min_length=1)
    dependencies: list[int] = Field(default_factory=list)
    status: QueueItemStatus = QueueItemStatus.PENDING
    attempts: int = Field(default=0, ge=0)
    error: str | None = None


class ExecutionStatistics(BaseModel):
    """Compact, persisted sequential Batch execution counters."""

    model_config = ConfigDict(frozen=True)

    total: int = Field(default=0, ge=0)
    completed: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    skipped: int = Field(default=0, ge=0)
    attempts: int = Field(default=0, ge=0)
    elapsed_time: float = Field(default=0.0, ge=0.0)


class ProgressSnapshot(BaseModel):
    """Read-only progress snapshot updated at each sequential checkpoint."""

    model_config = ConfigDict(frozen=True)

    total: int = Field(default=0, ge=0)
    completed: int = Field(default=0, ge=0)
    current_page: int | None = None
    next_page: int | None = None


class ResumeCheckpoint(BaseModel):
    """Persisted checkpoint that makes resumption inspectable without replay."""

    model_config = ConfigDict(frozen=True)

    completed_pages: list[int] = Field(default_factory=list)
    next_page: int | None = None


class RetrySummary(BaseModel):
    """Persisted summary of the latest failed-page retry request."""

    model_config = ConfigDict(frozen=True)

    retry_count: int = Field(default=0, ge=0)
    requeued_pages: list[int] = Field(default_factory=list)


class BatchRecord(BaseModel):
    """Repository-persisted Batch snapshot stored inside Project.workflow."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    chapter_ids: list[str] = Field(default_factory=list)
    policy: ExecutionPolicyName
    status: BatchStatus = BatchStatus.PLANNED
    queue: list[QueueItem] = Field(default_factory=list)
    logs: list[str] = Field(default_factory=list)
    events: list[WorkflowEvent] = Field(default_factory=list)
    statistics: ExecutionStatistics = Field(default_factory=ExecutionStatistics)
    progress: ProgressSnapshot = Field(default_factory=ProgressSnapshot)
    checkpoint: ResumeCheckpoint = Field(default_factory=ResumeCheckpoint)
    retry_summary: RetrySummary = Field(default_factory=RetrySummary)


class ExecutionResult(BaseModel):
    """Stable result summary for Batch run, resume, retry, and status operations."""

    model_config = ConfigDict(frozen=True)

    success: bool
    completed: list[int] = Field(default_factory=list)
    failed: list[int] = Field(default_factory=list)
    skipped: list[int] = Field(default_factory=list)
    elapsed_time: float = Field(ge=0.0)
    logs: list[str] = Field(default_factory=list)
    batch_id: str = ""
    status: BatchStatus = BatchStatus.PLANNED
    statistics: ExecutionStatistics = Field(default_factory=ExecutionStatistics)
    progress: ProgressSnapshot = Field(default_factory=ProgressSnapshot)
    checkpoint: ResumeCheckpoint = Field(default_factory=ResumeCheckpoint)
    retry_summary: RetrySummary = Field(default_factory=RetrySummary)


class ExecutionQueue(Protocol):
    """FIFO queue port used by a Batch workflow execution."""

    def enqueue(self, item: QueueItem) -> None: ...

    def dequeue(self) -> QueueItem | None: ...

    def peek(self) -> QueueItem | None: ...

    def clear(self) -> None: ...

    def size(self) -> int: ...


class Worker(Protocol):
    """A Page-scoped worker that may call only the existing WorkflowEngine."""

    def run(self, page_context: WorkflowContext) -> WorkflowResult: ...


class InMemoryExecutionQueue:
    """Small FIFO implementation reconstructed from persisted QueueItem values."""

    def __init__(self, items: Iterable[QueueItem] = ()) -> None:
        self._items: deque[QueueItem] = deque(items)

    def enqueue(self, item: QueueItem) -> None:
        self._items.append(item)

    def dequeue(self) -> QueueItem | None:
        return self._items.popleft() if self._items else None

    def peek(self) -> QueueItem | None:
        return self._items[0] if self._items else None

    def clear(self) -> None:
        self._items.clear()

    def size(self) -> int:
        return len(self._items)
