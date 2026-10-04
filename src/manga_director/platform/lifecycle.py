"""Descriptive unified lifecycle management without lifecycle ownership."""

from __future__ import annotations

from pydantic import Field

from manga_director.platform.foundation import UnifiedCreativeContextDTO
from manga_director.production.director import DirectorModel


class UnifiedLifecycleReferenceDTO(DirectorModel):
    lifecycle_id: str
    subject_type: str
    subject_id: str
    source_module: str
    stage: str
    page_count: int = Field(default=1, ge=1, le=1)
    state_transitioned: bool = False
    reference_persisted: bool = False


class UnifiedLifecycleReport(DirectorModel):
    context: UnifiedCreativeContextDTO
    references: tuple[UnifiedLifecycleReferenceDTO, ...]
    reference_count: int = Field(default=0, ge=0)
    lifecycle_owner_transferred: bool = False
    retention_enforced: bool = False
    recovery_attempted: bool = False
    planning_only: bool = True


class UnifiedLifecycleService:
    """Builds source-linked lifecycle references and never changes their owner."""

    def report(self, context: UnifiedCreativeContextDTO) -> UnifiedLifecycleReport:
        references = (
            UnifiedLifecycleReferenceDTO(
                lifecycle_id=f"project:{context.project_id}",
                subject_type="project",
                subject_id=context.project_id,
                source_module="project",
                stage="referenced",
            ),
            UnifiedLifecycleReferenceDTO(
                lifecycle_id=f"page:{context.page_reference}",
                subject_type="page",
                subject_id=context.page_reference,
                source_module="workflow",
                stage=context.workflow_state,
            ),
        )
        return UnifiedLifecycleReport(
            context=context, references=references, reference_count=len(references)
        )

