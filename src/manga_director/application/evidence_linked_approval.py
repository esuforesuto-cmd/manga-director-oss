"""Private Application gate for one explicit evidence-linked approval."""

from __future__ import annotations

from typing import Any, cast

from manga_director.application.human_visual_review_evidence import _payload
from manga_director.application.human_visual_review_readiness import (
    HumanVisualReviewReadinessService,
    ReviewChecklistDecision,
    _HumanVisualReviewReadinessProof,
)
from manga_director.application.workflow import WorkflowApplicationService
from manga_director.domain.state_machine import PageState
from manga_director.production.next_generation_durable_human_visual_review_evidence import (
    DurableHumanVisualReviewEvidenceUnavailable,
    LocalDurableHumanVisualReviewEvidenceOwner,
    _HumanVisualReviewEvidencePayload,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.local_file_durability import RevisionedProjectSnapshot
from manga_director.workflow.contracts import WorkflowContext
from manga_director.workflow.durable_execution import LocalFileDurablePageStore


class EvidenceLinkedApprovalUnavailable(ValueError):
    """Redacted failure for unavailable evidence-linked approval."""


class EvidenceLinkedApprovalService:
    """Re-prove one exact stored review under the durable Page fence."""

    def __init__(
        self,
        repository: LocalFileRepository,
        workflow: WorkflowApplicationService,
        readiness: HumanVisualReviewReadinessService,
        owner: LocalDurableHumanVisualReviewEvidenceOwner,
    ) -> None:
        self._repository = repository
        self._workflow = workflow
        self._readiness = readiness
        self._owner = owner
        self._page_store = LocalFileDurablePageStore(repository)

    def approve(
        self,
        project_id: str,
        page_number: int,
        *,
        approved_by: str,
        review_id: str,
    ) -> Any:
        try:
            return self._workflow._approve_page_with_evidence(
                project_id,
                page_number,
                approved_by,
                review_id,
                self,
            )
        except Exception as error:
            raise EvidenceLinkedApprovalUnavailable(
                "evidence-linked approval is unavailable"
            ) from error

    def _prove_under_fence(
        self,
        snapshot: RevisionedProjectSnapshot,
        context: WorkflowContext,
        project_id: str,
        page_id: str,
        review_id: str,
    ) -> _HumanVisualReviewReadinessProof:
        proof: _HumanVisualReviewReadinessProof | None = None
        try:
            self._require_fresh_context(snapshot, context, project_id, page_id)
            stored = self._owner._read_exact(review_id)
            if stored is None:
                raise EvidenceLinkedApprovalUnavailable(
                    "evidence-linked approval is unavailable"
                )
            self._require_ready_stored_record(
                stored,
                project_id,
                page_id,
                snapshot.project.page(int(page_id)).page_number,
            )
            proof = self._readiness._prove(
                project_id,
                int(page_id),
                reviewer_id=stored.reviewer_id,
                reviewed_at=stored.reviewed_at,
                checklist=tuple(
                    ReviewChecklistDecision(
                        criterion=item.criterion,
                        outcome=item.outcome,
                        rationale=item.rationale,
                    )
                    for item in stored.checklist
                ),
                overall_judgment=stored.overall_judgment,
                rationale=stored.rationale,
            )
            if (
                not proof._workflow_consistency.valid
                or _payload(proof.report) != stored
            ):
                raise EvidenceLinkedApprovalUnavailable(
                    "evidence-linked approval is unavailable"
                )
            self._require_fresh_context(snapshot, context, project_id, page_id)
            return proof
        except EvidenceLinkedApprovalUnavailable:
            if proof is not None:
                proof.release()
            raise
        except DurableHumanVisualReviewEvidenceUnavailable as error:
            if proof is not None:
                proof.release()
            raise EvidenceLinkedApprovalUnavailable(
                "evidence-linked approval is unavailable"
            ) from error
        except Exception as error:
            if proof is not None:
                proof.release()
            raise EvidenceLinkedApprovalUnavailable(
                "evidence-linked approval is unavailable"
            ) from error

    def _require_fresh_context(
        self,
        expected: RevisionedProjectSnapshot,
        context: WorkflowContext,
        project_id: str,
        page_id: str,
    ) -> None:
        current = self._page_store.load_revisioned(project_id)
        if (
            expected.project.id != project_id
            or current.revision != expected.revision
            or current.fingerprint != expected.fingerprint
            or current.project != expected.project
            or self._page_store.context_from_snapshot(current, page_id) != context
            or context.page != {"project_id": project_id, "page_id": page_id}
            or context.state is not PageState.QUALITY_CHECKED
            or PageState.APPROVED.value in context.artifacts
        ):
            raise EvidenceLinkedApprovalUnavailable(
                "evidence-linked approval is unavailable"
            )

    @staticmethod
    def _require_ready_stored_record(
        stored: _HumanVisualReviewEvidencePayload,
        project_id: str,
        page_id: str,
        page_number: int,
    ) -> None:
        if (
            stored.project_id != project_id
            or stored.page_id != page_id
            or stored.page_number != page_number
            or stored.page_state != PageState.QUALITY_CHECKED.value
            or stored.status != "ready"
            or stored.ready is not True
            or stored.findings
            or stored.missing_prerequisites
            or stored.overall_judgment != "acceptable_for_approval_consideration"
            or any(
                item.outcome not in {"acceptable", "not_applicable"}
                for item in stored.checklist
            )
        ):
            raise EvidenceLinkedApprovalUnavailable(
                "evidence-linked approval is unavailable"
            )


def build_evidence_linked_approval(
    repository: LocalFileRepository,
    workflow: WorkflowApplicationService,
    readiness: HumanVisualReviewReadinessService,
) -> EvidenceLinkedApprovalService:
    return EvidenceLinkedApprovalService(
        repository,
        workflow,
        readiness,
        LocalDurableHumanVisualReviewEvidenceOwner(
            repository._next_generation_normal_execution_owner_root()
        ),
    )


def attach_evidence_linked_approval(
    application: object,
    service: EvidenceLinkedApprovalService,
) -> None:
    cast(Any, application)._evidence_linked_approval = service


def evidence_linked_approval_for(
    application: object,
) -> EvidenceLinkedApprovalService | None:
    service = getattr(application, "_evidence_linked_approval", None)
    return service if isinstance(service, EvidenceLinkedApprovalService) else None


__all__ = ()
