"""Private read-only Application service for durable visual review history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, cast

from manga_director.domain.state_machine import PageState
from manga_director.production.next_generation_durable_human_visual_review_evidence import (
    DurableHumanVisualReviewEvidenceUnavailable,
    LocalDurableHumanVisualReviewEvidenceOwner,
)
from manga_director.production.next_generation_human_visual_qa_approval_readiness import (
    HumanVisualCriterion,
    HumanVisualOutcome,
    OverallHumanJudgment,
)
from manga_director.repositories.local_file import LocalFileRepository

_HISTORY_STATES = {
    PageState.GENERATED,
    PageState.QUALITY_CHECKED,
    PageState.APPROVED,
}


class HumanVisualReviewEvidenceHistoryUnavailable(ValueError):
    """Redacted failure for unavailable authoritative Page history."""


class HumanVisualReviewEvidenceHistoryPersistenceUnavailable(ValueError):
    """Redacted failure for unavailable read-only evidence storage."""


@dataclass(frozen=True, slots=True)
class HumanVisualReviewEvidenceHistoryChecklistItem:
    criterion: HumanVisualCriterion
    outcome: HumanVisualOutcome
    rationale: str


@dataclass(frozen=True, slots=True)
class HumanVisualReviewEvidenceHistoryFinding:
    code: str
    status: Literal["needs_review", "blocked"]
    message: str
    criterion: str


@dataclass(frozen=True, slots=True)
class HumanVisualReviewEvidenceHistoryRecord:
    review_id: str
    output_asset_id: str
    reviewer_id: str
    reviewed_at: datetime
    page_state: Literal["Generated", "QualityChecked"]
    checklist: tuple[HumanVisualReviewEvidenceHistoryChecklistItem, ...]
    overall_judgment: OverallHumanJudgment
    rationale: str
    status: Literal["ready", "needs_review", "blocked"]
    ready: bool
    findings: tuple[HumanVisualReviewEvidenceHistoryFinding, ...]
    missing_prerequisites: tuple[str, ...]
    analysis_only: Literal[True] = True


@dataclass(frozen=True, slots=True)
class HumanVisualReviewEvidenceHistoryResult:
    page_number: int
    records: tuple[HumanVisualReviewEvidenceHistoryRecord, ...]
    complete: Literal[True] = True
    read_only: Literal[True] = True
    analysis_only: Literal[True] = True


class HumanVisualReviewEvidenceHistoryService:
    """Bind immutable owner records to one authoritative persisted Page."""

    def __init__(
        self,
        repository: LocalFileRepository,
        owner: LocalDurableHumanVisualReviewEvidenceOwner,
    ) -> None:
        self._repository = repository
        self._owner = owner

    def get(
        self,
        project_id: str,
        page_number: int,
    ) -> HumanVisualReviewEvidenceHistoryResult:
        try:
            page = self._repository._load_authoritative_page(project_id, page_number)
            if page.state not in _HISTORY_STATES:
                raise HumanVisualReviewEvidenceHistoryUnavailable(
                    "human visual review evidence history is unavailable"
                )
        except HumanVisualReviewEvidenceHistoryUnavailable:
            raise
        except Exception as error:
            raise HumanVisualReviewEvidenceHistoryUnavailable(
                "human visual review evidence history is unavailable"
            ) from error
        try:
            payloads = self._owner.read_page_history(
                project_id,
                str(page.page_number),
                page.page_number,
            )
        except DurableHumanVisualReviewEvidenceUnavailable as error:
            raise HumanVisualReviewEvidenceHistoryPersistenceUnavailable(
                "human visual review evidence history persistence is unavailable"
            ) from error
        records = tuple(
            HumanVisualReviewEvidenceHistoryRecord(
                review_id=payload.review_id,
                output_asset_id=payload.output_asset_id,
                reviewer_id=payload.reviewer_id,
                reviewed_at=payload.reviewed_at,
                page_state=payload.page_state,
                checklist=tuple(
                    HumanVisualReviewEvidenceHistoryChecklistItem(
                        criterion=item.criterion,
                        outcome=item.outcome,
                        rationale=item.rationale,
                    )
                    for item in payload.checklist
                ),
                overall_judgment=payload.overall_judgment,
                rationale=payload.rationale,
                status=payload.status,
                ready=payload.ready,
                findings=tuple(
                    HumanVisualReviewEvidenceHistoryFinding(
                        code=item.code,
                        status=item.status,
                        message=item.message,
                        criterion=item.criterion,
                    )
                    for item in payload.findings
                ),
                missing_prerequisites=payload.missing_prerequisites,
            )
            for payload in payloads
        )
        return HumanVisualReviewEvidenceHistoryResult(
            page_number=page.page_number,
            records=records,
        )


def build_human_visual_review_evidence_history(
    repository: LocalFileRepository,
) -> HumanVisualReviewEvidenceHistoryService:
    return HumanVisualReviewEvidenceHistoryService(
        repository,
        LocalDurableHumanVisualReviewEvidenceOwner(
            repository._next_generation_normal_execution_owner_root()
        ),
    )


def attach_human_visual_review_evidence_history(
    application: object,
    service: HumanVisualReviewEvidenceHistoryService,
) -> None:
    cast(Any, application)._human_visual_review_evidence_history = service


def human_visual_review_evidence_history_for(
    application: object,
) -> HumanVisualReviewEvidenceHistoryService | None:
    service = getattr(application, "_human_visual_review_evidence_history", None)
    return (
        service
        if isinstance(service, HumanVisualReviewEvidenceHistoryService)
        else None
    )


__all__ = ()
