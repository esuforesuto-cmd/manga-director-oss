"""Private Application writer for durable local human visual review evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, cast

from manga_director.application.human_visual_review_readiness import (
    HumanVisualReviewReadinessFinding,
    HumanVisualReviewReadinessService,
    HumanVisualReviewReadinessUnavailable,
    ReadinessStatus,
    ReviewChecklistDecision,
    ReviewOverallJudgment,
)
from manga_director.production.next_generation_durable_human_visual_review_evidence import (
    DurableHumanVisualReviewEvidenceUnavailable,
    LocalDurableHumanVisualReviewEvidenceOwner,
    _EvidenceChecklistItem,
    _EvidenceFinding,
    _HumanVisualReviewEvidencePayload,
)
from manga_director.production.next_generation_human_visual_qa_approval_readiness import (
    HumanVisualQAApprovalReadinessReport,
)
from manga_director.production.next_generation_page_output_proof import (
    DeterministicCompositionPageOutputProof,
    ResolvedPageOutput,
)
from manga_director.repositories.local_file import LocalFileRepository


class HumanVisualReviewEvidenceUnavailable(ValueError):
    """Redacted failure for unavailable authoritative review evidence."""


class HumanVisualReviewEvidencePersistenceUnavailable(ValueError):
    """Redacted failure for unavailable durable persistence."""


@dataclass(frozen=True, slots=True)
class HumanVisualReviewEvidenceResult:
    status: ReadinessStatus
    ready: bool
    page_state: str
    findings: tuple[HumanVisualReviewReadinessFinding, ...]
    missing_prerequisites: tuple[str, ...]
    evidence_recorded: Literal[True] = True
    idempotent_replay: bool = False
    analysis_only: Literal[True] = True


class HumanVisualReviewEvidenceService:
    """Persist one canonical report while its exact-file lease remains held."""

    def __init__(
        self,
        readiness: HumanVisualReviewReadinessService,
        owner: LocalDurableHumanVisualReviewEvidenceOwner,
    ) -> None:
        self._readiness = readiness
        self._owner = owner

    def record(
        self,
        project_id: str,
        page_number: int,
        *,
        reviewer_id: str,
        reviewed_at: datetime,
        checklist: tuple[ReviewChecklistDecision, ...],
        overall_judgment: ReviewOverallJudgment,
        rationale: str,
    ) -> HumanVisualReviewEvidenceResult:
        proof = None
        try:
            proof = self._readiness._prove(
                project_id,
                page_number,
                reviewer_id=reviewer_id,
                reviewed_at=reviewed_at,
                checklist=checklist,
                overall_judgment=overall_judgment,
                rationale=rationale,
            )
            report = proof.report
            if not proof._workflow_consistency.valid:
                raise HumanVisualReviewEvidenceUnavailable(
                    "human visual review evidence is unavailable"
                )
            payload = _payload(report)
            try:
                write = self._owner.persist(payload)
            except DurableHumanVisualReviewEvidenceUnavailable as error:
                raise HumanVisualReviewEvidencePersistenceUnavailable(
                    "human visual review evidence persistence is unavailable"
                ) from error
            result = HumanVisualReviewEvidenceResult(
                status=report.status,
                ready=report.ready,
                page_state=report.persisted_page_state.value,
                findings=tuple(
                    HumanVisualReviewReadinessFinding(
                        code=item.code,
                        status=item.status,
                        message=item.message,
                        criterion=item.criterion,
                    )
                    for item in report.findings
                ),
                missing_prerequisites=report.missing_prerequisites,
                idempotent_replay=write.outcome == "confirmed",
            )
        except HumanVisualReviewEvidencePersistenceUnavailable:
            raise
        except HumanVisualReviewReadinessUnavailable as error:
            raise HumanVisualReviewEvidenceUnavailable(
                "human visual review evidence is unavailable"
            ) from error
        except Exception as error:
            raise HumanVisualReviewEvidenceUnavailable(
                "human visual review evidence is unavailable"
            ) from error
        finally:
            if proof is not None:
                proof.release()
        return result

    def require_pre_quality_evidence(
        self,
        project_id: str,
        page_id: str,
        expected_proof: DeterministicCompositionPageOutputProof,
    ) -> str | None:
        """Require one exact, persisted Generated review before composite Quality."""

        unavailable = "PANEL_VISUAL_QA_EVIDENCE_REQUIRED"
        readiness_proof = None
        try:
            page_number = int(page_id)
            if (
                str(page_number) != page_id
                or page_number < 1
                or expected_proof.project_id != project_id
                or expected_proof.page_id != page_id
                or not expected_proof.ordered_sources
            ):
                return unavailable

            history = self._owner.read_page_history(project_id, page_id, page_number)
            candidates = tuple(
                item
                for item in history
                if item.project_id == project_id
                and item.page_id == page_id
                and item.page_number == page_number
                and item.attempt_id == expected_proof.attempt_id
                and item.output_asset_id == expected_proof.asset_id
                and item.provenance_reference == expected_proof.provenance_reference
            )
            if len(candidates) != 1:
                return unavailable
            stored = candidates[0]
            if stored.page_state != "Generated":
                return unavailable

            checklist = tuple(
                ReviewChecklistDecision.model_validate(item.model_dump())
                for item in stored.checklist
            )
            readiness_proof = self._readiness._prove(
                project_id,
                page_number,
                reviewer_id=stored.reviewer_id,
                reviewed_at=stored.reviewed_at,
                checklist=checklist,
                overall_judgment=stored.overall_judgment,
                rationale=stored.rationale,
            )
            report = readiness_proof.report
            resolved_output = readiness_proof._asset_proof
            if (
                not readiness_proof._workflow_consistency.valid
                or report.persisted_page_state.value != "Generated"
                or not isinstance(resolved_output, ResolvedPageOutput)
                or resolved_output.proof != expected_proof
                or report.scope.project_id != project_id
                or report.scope.page_id != page_id
                or report.scope.attempt_id != expected_proof.attempt_id
                or report.scope.output_asset_id != expected_proof.asset_id
                or report.scope.provenance_reference
                != expected_proof.provenance_reference
                or _payload(report) != stored
                or report.status != "needs_review"
                or report.ready
                or report.missing_prerequisites != ("QUALITY_CHECK_REQUIRED",)
                or len(report.findings) != 1
                or report.findings[0].code != "QUALITY_CHECK_REQUIRED"
                or report.findings[0].status != "needs_review"
            ):
                return unavailable
            return None
        except Exception:
            return unavailable
        finally:
            if readiness_proof is not None:
                readiness_proof.release()


def _payload(
    report: HumanVisualQAApprovalReadinessReport,
) -> _HumanVisualReviewEvidencePayload:
    judgment = report.human_judgment
    if judgment is None or report.persisted_page_state.value not in {
        "Generated",
        "QualityChecked",
    }:
        raise HumanVisualReviewEvidenceUnavailable(
            "human visual review evidence is unavailable"
        )
    return _HumanVisualReviewEvidencePayload(
        review_id=judgment.review_id,
        project_id=report.scope.project_id,
        page_id=report.scope.page_id,
        page_number=report.scope.page_number,
        page_state=cast(Literal["Generated", "QualityChecked"], report.persisted_page_state.value),
        attempt_id=report.scope.attempt_id,
        output_asset_id=report.scope.output_asset_id,
        provenance_reference=report.scope.provenance_reference,
        qa_report_reference=report.scope.qa_report_reference,
        reviewer_id=judgment.reviewer_id,
        reviewed_at=judgment.reviewed_at,
        checklist=tuple(
            _EvidenceChecklistItem(
                criterion=item.criterion,
                outcome=item.outcome,
                rationale=item.rationale,
            )
            for item in judgment.checklist
        ),
        overall_judgment=judgment.overall_judgment,
        rationale=judgment.rationale,
        status=report.status,
        ready=report.ready,
        findings=tuple(
            _EvidenceFinding(
                code=item.code,
                status=item.status,
                message=item.message,
                criterion=item.criterion,
            )
            for item in report.findings
        ),
        missing_prerequisites=report.missing_prerequisites,
    )


def build_human_visual_review_evidence(
    repository: LocalFileRepository,
    readiness: HumanVisualReviewReadinessService,
) -> HumanVisualReviewEvidenceService:
    return HumanVisualReviewEvidenceService(
        readiness,
        LocalDurableHumanVisualReviewEvidenceOwner(
            repository._next_generation_normal_execution_owner_root()
        ),
    )


def attach_human_visual_review_evidence(
    application: object,
    service: HumanVisualReviewEvidenceService,
) -> None:
    cast(Any, application)._human_visual_review_evidence = service


def human_visual_review_evidence_for(
    application: object,
) -> HumanVisualReviewEvidenceService | None:
    service = getattr(application, "_human_visual_review_evidence", None)
    return service if isinstance(service, HumanVisualReviewEvidenceService) else None


__all__ = ()
