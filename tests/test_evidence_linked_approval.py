from __future__ import annotations

import os
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast

import pytest

from manga_director.agents.builtin import ApprovalAgent
from manga_director.application.evidence_linked_approval import (
    EvidenceLinkedApprovalService,
    EvidenceLinkedApprovalUnavailable,
)
from manga_director.application.human_visual_review_evidence import _payload
from manga_director.application.human_visual_review_readiness import (
    _HumanVisualReviewReadinessProof,
)
from manga_director.application.workflow import WorkflowApplicationService
from manga_director.domain.project import Page, Project
from manga_director.domain.state_machine import PageState, StateMachine
from manga_director.events import MemoryEventBus
from manga_director.production.next_generation_durable_human_visual_review_evidence import (
    LocalDurableHumanVisualReviewEvidenceOwner,
)
from manga_director.production.next_generation_human_visual_qa_approval_readiness import (
    ApprovalReadinessScopeDTO,
    HumanVisualChecklistDecisionDTO,
    HumanVisualJudgmentDTO,
    HumanVisualQAApprovalReadinessReport,
)
from manga_director.production.reliability import WorkflowConsistencyReport
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.local_file_durability import RevisionedProjectSnapshot
from manga_director.repositories.project_loader import ProjectLoader
from manga_director.workflow.durable_execution import LocalFileDurablePageStore
from manga_director.workflow.engine import WorkflowEngine

_CRITERIA = (
    "character_identity",
    "face",
    "costume",
    "props",
    "pose",
    "gaze",
    "emotion",
    "screen_direction",
    "location",
    "time",
    "composition",
    "panel_intent",
    "visible_corruption",
    "truncation",
    "watermark",
    "unsafe_content",
    "unintended_text",
    "continuity_comparison",
)


class _Lease:
    def __init__(self) -> None:
        self.release_calls = 0

    def release(self) -> None:
        self.release_calls += 1


class _Repository:
    def __init__(self, snapshot: RevisionedProjectSnapshot) -> None:
        self.snapshot = snapshot
        self.loads = 0

    def _load_revisioned(self, project_id: str) -> RevisionedProjectSnapshot:
        assert project_id == self.snapshot.project.id
        self.loads += 1
        return self.snapshot


class _Owner:
    def __init__(self, records: dict[str, object]) -> None:
        self.records = records
        self.reads: list[str] = []

    def _read_exact(self, review_id: str):
        self.reads.append(review_id)
        return self.records.get(review_id)


class _Readiness:
    def __init__(self, report: HumanVisualQAApprovalReadinessReport) -> None:
        self.report = report
        self.calls: list[dict[str, object]] = []
        self.leases: list[_Lease] = []

    def _prove(self, project_id: str, page_number: int, **submission):
        self.calls.append(
            {"project_id": project_id, "page_number": page_number, **submission}
        )
        lease = _Lease()
        self.leases.append(lease)
        return _HumanVisualReviewReadinessProof(
            report=self.report,
            _asset_proof=lease,  # type: ignore[arg-type]
            _workflow_consistency=WorkflowConsistencyReport(
                project_id=project_id,
                page_number=page_number,
                valid=True,
                current_state=PageState.QUALITY_CHECKED,
            ),
        )


def _report(*, review_id: str = "review:exact:001") -> HumanVisualQAApprovalReadinessReport:
    checklist = tuple(
        sorted(
            (
                HumanVisualChecklistDecisionDTO(
                    criterion=criterion,
                    outcome="acceptable",
                    rationale="Reviewed directly",
                )
                for criterion in _CRITERIA
            ),
            key=lambda item: (item.criterion, item.outcome, item.rationale),
        )
    )
    scope = ApprovalReadinessScopeDTO(
        project_id="demo",
        page_id="1",
        page_number=1,
        target_page_reference="page:demo:1",
        attempt_id="attempt:001",
        output_asset_id="asset:001",
        provenance_reference="provenance:001",
        qa_report_reference="qa-report:001",
    )
    return HumanVisualQAApprovalReadinessReport(
        scope=scope,
        persisted_page_state=PageState.QUALITY_CHECKED,
        human_judgment=HumanVisualJudgmentDTO(
            review_id=review_id,
            project_id="demo",
            page_id="1",
            attempt_id=scope.attempt_id,
            output_asset_id=scope.output_asset_id,
            provenance_reference=scope.provenance_reference,
            qa_report_reference=scope.qa_report_reference,
            reviewer_id="reviewer:local",
            reviewed_at=datetime(2026, 10, 21, tzinfo=UTC),
            checklist=checklist,
            overall_judgment="acceptable_for_approval_consideration",
            rationale="Ready for explicit approval consideration",
        ),
        findings=(),
        missing_prerequisites=(),
        status="ready",
        ready=True,
    )


def _snapshot() -> RevisionedProjectSnapshot:
    page = Page(
        page_number=1,
        state=PageState.QUALITY_CHECKED,
        image={"artifact_kind": "logical_output_asset", "output_asset_id": "asset:001"},
        quality={"passed": True},
        history=[
            {
                "kind": "workflow",
                "from": "Generated",
                "to": "QualityChecked",
                "step": "QualityChecked",
            }
        ],
    )
    return RevisionedProjectSnapshot(
        project=Project(id="demo", title="Demo", pages=[page]),
        revision=7,
        fingerprint="aggregate:fingerprint",
    )


def _service(report: HumanVisualQAApprovalReadinessReport | None = None):
    snapshot = _snapshot()
    repository = _Repository(snapshot)
    canonical_report = report or _report()
    owner = _Owner({canonical_report.human_judgment.review_id: _payload(canonical_report)})
    readiness = _Readiness(canonical_report)
    service = EvidenceLinkedApprovalService(
        repository,  # type: ignore[arg-type]
        SimpleNamespace(),  # type: ignore[arg-type]
        readiness,  # type: ignore[arg-type]
        owner,  # type: ignore[arg-type]
    )
    context = LocalFileDurablePageStore(repository).context_from_snapshot(snapshot, "1")  # type: ignore[arg-type]
    return service, repository, owner, readiness, snapshot, context


def test_gate_reads_only_the_explicit_id_and_replays_the_complete_stored_submission() -> None:
    service, repository, owner, readiness, snapshot, context = _service()

    proof = service._prove_under_fence(
        snapshot,
        context,
        "demo",
        "1",
        "review:exact:001",
    )

    assert owner.reads == ["review:exact:001"]
    assert repository.loads == 2
    assert len(readiness.calls) == 1
    assert readiness.calls[0]["reviewer_id"] == "reviewer:local"
    assert readiness.calls[0]["overall_judgment"] == (
        "acceptable_for_approval_consideration"
    )
    assert len(readiness.calls[0]["checklist"]) == 18
    assert readiness.leases[0].release_calls == 0
    proof.release()
    assert readiness.leases[0].release_calls == 1


def test_gate_never_falls_back_to_another_record() -> None:
    service, _repository, owner, readiness, snapshot, context = _service()

    with pytest.raises(EvidenceLinkedApprovalUnavailable):
        service._prove_under_fence(
            snapshot,
            context,
            "demo",
            "1",
            "review:missing",
        )

    assert owner.reads == ["review:missing"]
    assert readiness.calls == []


def test_gate_rejects_non_ready_stored_evidence_before_current_reproof() -> None:
    service, _repository, owner, readiness, snapshot, context = _service()
    stored = owner.records["review:exact:001"]
    owner.records["review:exact:001"] = stored.model_copy(  # type: ignore[union-attr]
        update={
            "status": "needs_review",
            "ready": False,
            "missing_prerequisites": ("QUALITY_CHECK_REQUIRED",),
        }
    )

    with pytest.raises(EvidenceLinkedApprovalUnavailable):
        service._prove_under_fence(
            snapshot,
            context,
            "demo",
            "1",
            "review:exact:001",
        )

    assert readiness.calls == []


def test_gate_rejects_fresh_revision_change_before_reading_evidence() -> None:
    service, repository, owner, readiness, snapshot, context = _service()
    repository.snapshot = RevisionedProjectSnapshot(
        project=snapshot.project,
        revision=snapshot.revision + 1,
        fingerprint="aggregate:changed",
    )

    with pytest.raises(EvidenceLinkedApprovalUnavailable):
        service._prove_under_fence(
            snapshot,
            context,
            "demo",
            "1",
            "review:exact:001",
        )

    assert owner.reads == []
    assert readiness.calls == []


def test_gate_releases_current_asset_proof_when_canonical_payload_differs() -> None:
    service, _repository, owner, readiness, snapshot, context = _service()
    mismatched = _report(review_id="review:other")
    readiness.report = mismatched

    with pytest.raises(EvidenceLinkedApprovalUnavailable):
        service._prove_under_fence(
            snapshot,
            context,
            "demo",
            "1",
            "review:exact:001",
        )

    assert owner.reads == ["review:exact:001"]
    assert readiness.leases[0].release_calls == 1


@pytest.mark.skipif(
    os.name != "nt",
    reason="durable LocalFile Page fencing is available only on Windows",
)
def test_real_linked_approval_preserves_evidence_bytes_and_survives_restart(
    tmp_path,
) -> None:
    repository_root = tmp_path / "repository"
    repository = LocalFileRepository(repository_root)
    snapshot = _snapshot()
    page = snapshot.project.page(1).model_copy(
        update={
            "page_design": {},
            "review": {},
            "storyboard": {},
            "prompt": {},
        }
    )
    repository.save(snapshot.project.replace_page(page))
    report = _report()
    repository._next_generation_normal_execution_owner_root().mkdir(
        parents=True,
        exist_ok=True,
    )
    owner = LocalDurableHumanVisualReviewEvidenceOwner(
        repository._next_generation_normal_execution_owner_root()
    )
    assert owner.persist(_payload(report)).outcome == "recorded"
    evidence_root = (
        repository._next_generation_normal_execution_owner_root()
        / "review-evidence"
    )
    before = {
        path.relative_to(evidence_root).as_posix(): path.read_bytes()
        for path in evidence_root.rglob("*")
        if path.is_file()
    }
    readiness = _Readiness(report)
    engine = WorkflowEngine(
        state_machine=StateMachine(),
        event_bus=MemoryEventBus(),
        agents={PageState.APPROVED: ApprovalAgent()},
    )
    application = WorkflowApplicationService(
        engine,
        cast(Any, SimpleNamespace()),
        ProjectLoader(repository),
        repository,
    )
    service = EvidenceLinkedApprovalService(
        repository,
        application,
        cast(Any, readiness),
        owner,
    )

    service.approve(
        "demo",
        1,
        approved_by="editor:local",
        review_id="review:exact:001",
    )

    after = {
        path.relative_to(evidence_root).as_posix(): path.read_bytes()
        for path in evidence_root.rglob("*")
        if path.is_file()
    }
    restarted = LocalFileRepository(repository_root).load("demo").page(1)
    assert restarted.state is PageState.APPROVED
    assert restarted.approval == {
        "approved_by": "editor:local",
        "review_evidence_id": "review:exact:001",
    }
    assert before == after
    assert readiness.leases[0].release_calls == 1
