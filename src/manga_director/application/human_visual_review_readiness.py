"""Transport-neutral private use case for transient human visual readiness."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, cast

from manga_director.domain.project import Page
from manga_director.domain.state_machine import PageState
from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    DurableEvidenceWorkflowBindingReport,
)
from manga_director.production.next_generation_generation_evidence import (
    EvidenceValueDTO,
    GenerationEvidenceEnvelopeDTO,
    GenerationEvidenceValidationReport,
    GenerationEvidenceValidationService,
    GenerationIdentityBindingDTO,
)
from manga_director.production.next_generation_human_visual_qa_approval_readiness import (
    ApprovalReadinessScopeDTO,
    HumanVisualChecklistDecisionDTO,
    HumanVisualCriterion,
    HumanVisualJudgmentDTO,
    HumanVisualOutcome,
    HumanVisualQAApprovalReadinessReport,
    HumanVisualQAApprovalReadinessService,
    OverallHumanJudgment,
)
from manga_director.production.next_generation_page_output_proof import (
    DeterministicCompositionPageOutputProof,
    PageOutputProofUnavailable,
    PageOutputResolverPort,
    ResolvedPageOutput,
)
from manga_director.production.next_generation_safe_local_generated_asset_presentation import (
    SafeLocalGeneratedAssetPresenter,
    _SafeLocalGeneratedAssetProof,
)
from manga_director.production.next_generation_visual_continuity_qa import (
    ContinuityCharacterEvidenceDTO,
    ContinuityComparisonDTO,
    PanelContinuityEvidenceDTO,
    VisualContinuityQAReport,
    VisualContinuityQAService,
)
from manga_director.production.next_generation_workflow_application_ledger import (
    WorkflowApplicationLedgerBindingDTO,
)
from manga_director.production.reliability import WorkflowConsistencyReport
from manga_director.repositories.local_file import LocalFileRepository

ReadinessStatus = Literal["ready", "needs_review", "blocked"]
ReviewCriterion = HumanVisualCriterion
ReviewOutcome = HumanVisualOutcome
ReviewOverallJudgment = OverallHumanJudgment
ReviewChecklistDecision = HumanVisualChecklistDecisionDTO

_ASSESSABLE_STATES = {PageState.GENERATED, PageState.QUALITY_CHECKED}


class HumanVisualReviewReadinessUnavailable(ValueError):
    """Redacted application failure for unavailable authoritative evidence."""


@dataclass(frozen=True, slots=True)
class HumanVisualReviewReadinessFinding:
    code: str
    status: str
    message: str
    criterion: str


@dataclass(frozen=True, slots=True)
class HumanVisualReviewReadinessResult:
    status: ReadinessStatus
    ready: bool
    page_state: str
    findings: tuple[HumanVisualReviewReadinessFinding, ...]
    missing_prerequisites: tuple[str, ...]
    analysis_only: Literal[True] = True


@dataclass(frozen=True, slots=True, repr=False)
class _HumanVisualReviewSubmission:
    reviewer_id: str
    reviewed_at: datetime
    checklist: tuple[HumanVisualChecklistDecisionDTO, ...]
    overall_judgment: OverallHumanJudgment
    rationale: str

    def __repr__(self) -> str:
        return "_HumanVisualReviewSubmission(<redacted>)"


@dataclass(frozen=True, slots=True, repr=False)
class _HumanVisualReviewReadinessProof:
    """Canonical readiness report retained under the exact-file lease."""

    report: HumanVisualQAApprovalReadinessReport
    _asset_proof: _SafeLocalGeneratedAssetProof | ResolvedPageOutput = field(
        repr=False, compare=False
    )
    _workflow_consistency: WorkflowConsistencyReport = field(
        repr=False, compare=False
    )

    def __repr__(self) -> str:
        return "_HumanVisualReviewReadinessProof(<redacted>)"

    def release(self) -> None:
        self._asset_proof.release()


class HumanVisualReviewReadinessService:
    """Resolve one exact local proof and return only a redacted transient result."""

    def __init__(
        self,
        repository: LocalFileRepository,
        presenter: SafeLocalGeneratedAssetPresenter,
        page_output_resolver: PageOutputResolverPort | None = None,
    ) -> None:
        self._repository = repository
        self._presenter = presenter
        self._page_output_resolver = page_output_resolver
        self._readiness = HumanVisualQAApprovalReadinessService()

    def assess(
        self,
        project_id: str,
        page_number: int,
        *,
        reviewer_id: str,
        reviewed_at: datetime,
        checklist: tuple[HumanVisualChecklistDecisionDTO, ...],
        overall_judgment: OverallHumanJudgment,
        rationale: str,
    ) -> HumanVisualReviewReadinessResult:
        proof = self._prove(
            project_id,
            page_number,
            reviewer_id=reviewer_id,
            reviewed_at=reviewed_at,
            checklist=checklist,
            overall_judgment=overall_judgment,
            rationale=rationale,
        )
        try:
            return _redacted_result(proof.report)
        finally:
            proof.release()

    def _prove(  # noqa: C901 - closed legacy/composition proof branches stay explicit
        self,
        project_id: str,
        page_number: int,
        *,
        reviewer_id: str,
        reviewed_at: datetime,
        checklist: tuple[HumanVisualChecklistDecisionDTO, ...],
        overall_judgment: OverallHumanJudgment,
        rationale: str,
    ) -> _HumanVisualReviewReadinessProof:
        """Return one canonical report while retaining its exact-file proof."""

        asset_proof: _SafeLocalGeneratedAssetProof | ResolvedPageOutput | None = None
        try:
            page = self._repository._load_authoritative_page(project_id, page_number)
            if page.state not in _ASSESSABLE_STATES:
                raise HumanVisualReviewReadinessUnavailable(
                    "human visual review readiness is unavailable"
                )
            if self._page_output_resolver is None:
                asset_proof = self._presenter._prove(
                    project_id,
                    str(page.page_number),
                    _output_asset_id(page),
                )
                selected_attempt_id = asset_proof.binding.attempt_id
                selected_asset_id = asset_proof.binding.output_asset_id
                selected_provenance = asset_proof.evidence.provenance_reference
                target_page_reference = asset_proof.binding.target_page_reference
                evidence_report = GenerationEvidenceValidationService().validate(
                    (asset_proof.evidence,)
                )
                identity_bindings: Sequence[GenerationIdentityBindingDTO] = (
                    asset_proof.evidence.identity_bindings
                )
            else:
                asset_proof = self._page_output_resolver.resolve(
                    project_id,
                    str(page.page_number),
                    _output_asset_id(page),
                )
                selected_attempt_id = asset_proof.proof.attempt_id
                selected_asset_id = asset_proof.proof.asset_id
                selected_provenance = asset_proof.proof.provenance_reference
                target_page_reference = asset_proof.proof.target_page_reference
                if isinstance(
                    asset_proof.proof, DeterministicCompositionPageOutputProof
                ):
                    evidence_report = None
                    identity_bindings = ()
                else:
                    evidence = asset_proof.legacy_evidence
                    if not isinstance(evidence, GenerationEvidenceEnvelopeDTO):
                        raise HumanVisualReviewReadinessUnavailable(
                            "human visual review readiness is unavailable"
                        )
                    evidence_report = GenerationEvidenceValidationService().validate(
                        (evidence,)
                    )
                    identity_bindings = evidence.identity_bindings
            scope_seed = ApprovalReadinessScopeDTO(
                project_id=project_id,
                page_id=str(page.page_number),
                page_number=page.page_number,
                target_page_reference=target_page_reference,
                attempt_id=selected_attempt_id,
                output_asset_id=selected_asset_id,
                provenance_reference=selected_provenance,
                qa_report_reference="qa-report:pending",
            )
            visual_report = _visual_report(
                page,
                scope_seed,
                identity_bindings,
                evidence_report,
            )
            scope = scope_seed.model_copy(
                update={
                    "qa_report_reference": _logical_digest_reference(
                        "qa-report", visual_report.model_dump(mode="json")
                    )
                }
            )
            submission = _HumanVisualReviewSubmission(
                reviewer_id=reviewer_id,
                reviewed_at=reviewed_at,
                checklist=checklist,
                overall_judgment=overall_judgment,
                rationale=rationale,
            )
            workflow_consistency = _workflow_consistency(project_id, page)
            judgment = _human_judgment(project_id, page, scope, submission)
            if (
                isinstance(asset_proof, ResolvedPageOutput)
                and isinstance(
                    asset_proof.proof, DeterministicCompositionPageOutputProof
                )
            ):
                report = self._readiness._assess_composition_proof(
                    scope,
                    asset_proof.proof,
                    workflow_consistency,
                    visual_report,
                    human_judgment=judgment,
                )
            else:
                if evidence_report is None:
                    raise HumanVisualReviewReadinessUnavailable(
                        "human visual review readiness is unavailable"
                    )
                binding = (
                    asset_proof.binding
                    if isinstance(asset_proof, _SafeLocalGeneratedAssetProof)
                    else asset_proof.legacy_binding
                )
                if not isinstance(binding, WorkflowApplicationLedgerBindingDTO):
                    raise HumanVisualReviewReadinessUnavailable(
                        "human visual review readiness is unavailable"
                    )
                report = self._readiness._assess_server_resolved(
                    scope,
                    evidence_report,
                    _workflow_binding_report(binding),
                    workflow_consistency,
                    visual_report,
                    human_judgment=judgment,
                )
            return _HumanVisualReviewReadinessProof(
                report=report,
                _asset_proof=asset_proof,
                _workflow_consistency=workflow_consistency,
            )
        except HumanVisualReviewReadinessUnavailable:
            if asset_proof is not None:
                asset_proof.release()
            raise
        except PageOutputProofUnavailable as error:
            if asset_proof is not None:
                asset_proof.release()
            raise HumanVisualReviewReadinessUnavailable(
                "human visual review readiness is unavailable"
            ) from error
        except Exception as error:
            if asset_proof is not None:
                asset_proof.release()
            raise HumanVisualReviewReadinessUnavailable(
                "human visual review readiness is unavailable"
            ) from error


def _redacted_result(
    report: HumanVisualQAApprovalReadinessReport,
) -> HumanVisualReviewReadinessResult:
    return HumanVisualReviewReadinessResult(
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
    )


def _workflow_binding_report(
    binding: WorkflowApplicationLedgerBindingDTO,
) -> DurableEvidenceWorkflowBindingReport:
    return DurableEvidenceWorkflowBindingReport(
        attempt_id=binding.attempt_id,
        provider_reference=binding.provider_reference,
        output_asset_id=binding.output_asset_id,
        project_id=binding.project_id,
        page_id=binding.page_id,
        target_page_reference=binding.target_page_reference,
        status="eligible",
        eligible=True,
    )


def _human_judgment(
    project_id: str,
    page: Page,
    scope: ApprovalReadinessScopeDTO,
    submission: _HumanVisualReviewSubmission,
) -> HumanVisualJudgmentDTO:
    canonical_checklist = tuple(
        sorted(
            submission.checklist,
            key=lambda item: (item.criterion, item.outcome, item.rationale),
        )
    )
    return HumanVisualJudgmentDTO(
        review_id=_logical_digest_reference(
            "review",
            {
                "project_id": project_id,
                "page_number": page.page_number,
                "attempt_id": scope.attempt_id,
                "reviewer_id": submission.reviewer_id,
                "reviewed_at": submission.reviewed_at.isoformat(),
                "checklist": [item.model_dump(mode="json") for item in canonical_checklist],
                "overall_judgment": submission.overall_judgment,
                "rationale": submission.rationale,
            },
        ),
        project_id=project_id,
        page_id=str(page.page_number),
        attempt_id=scope.attempt_id,
        output_asset_id=scope.output_asset_id,
        provenance_reference=scope.provenance_reference,
        qa_report_reference=scope.qa_report_reference,
        reviewer_id=submission.reviewer_id,
        reviewed_at=submission.reviewed_at,
        checklist=canonical_checklist,
        overall_judgment=submission.overall_judgment,
        rationale=submission.rationale,
    )


def _output_asset_id(page: Page) -> str:
    image = page.image
    if (
        not isinstance(image, Mapping)
        or set(image) != {"artifact_kind", "output_asset_id"}
        or image.get("artifact_kind") != "logical_output_asset"
        or not isinstance(image.get("output_asset_id"), str)
    ):
        raise HumanVisualReviewReadinessUnavailable(
            "human visual review readiness is unavailable"
        )
    return cast(str, image["output_asset_id"])


def _workflow_consistency(project_id: str, page: Page) -> WorkflowConsistencyReport:
    entries = page.history
    valid_entries = all(isinstance(item, Mapping) for item in entries)
    workflow_entries = [
        item for item in entries if isinstance(item, Mapping) and item.get("kind") == "workflow"
    ]
    errors: list[str] = []
    if not valid_entries or not workflow_entries:
        errors.append("Persisted workflow history is unavailable.")
    elif workflow_entries[-1].get("to") != page.state.value:
        errors.append("Persisted workflow history does not match Page state.")
    generated = tuple(
        item
        for item in workflow_entries
        if item.get("from") == "PromptBuilt" and item.get("to") == "Generated"
    )
    if len(generated) != 1:
        errors.append("Persisted Generated transition is not unique.")
    return WorkflowConsistencyReport(
        project_id=project_id,
        page_number=page.page_number,
        valid=not errors,
        current_state=page.state,
        errors=errors,
    )


def _visual_report(
    page: Page,
    scope: ApprovalReadinessScopeDTO,
    identity_bindings: Sequence[GenerationIdentityBindingDTO],
    evidence_report: GenerationEvidenceValidationReport | None,
) -> VisualContinuityQAReport:
    previous = page.metadata.get("previous_page")
    current = page.metadata.get("current_page")
    if not isinstance(current, Mapping):
        return VisualContinuityQAService().validate(())
    if identity_bindings and not _explicit_character_id(current):
        return VisualContinuityQAService().validate(())
    comparison = ContinuityComparisonDTO(
        comparison_id=_logical_digest_reference(
            "comparison", {"previous": previous, "current": current}
        ),
        current_panel=_panel(current, scope, identity_bindings),
        previous_panel=(
            _panel(previous, scope, identity_bindings)
            if isinstance(previous, Mapping)
            else None
        ),
    )
    if evidence_report is None:
        return VisualContinuityQAService().validate((comparison,))
    return VisualContinuityQAService().validate(
        (comparison,), generation_evidence_validation_report=evidence_report
    )


def _panel(
    values: Mapping[object, object],
    scope: ApprovalReadinessScopeDTO,
    identity_bindings: Sequence[GenerationIdentityBindingDTO],
) -> PanelContinuityEvidenceDTO:
    page_id = _logical_value(values.get("page_id"))
    same_generated_page = page_id == scope.page_id
    characters: tuple[ContinuityCharacterEvidenceDTO, ...] = ()
    character_id = _explicit_character_id(values)
    if character_id is not None:
        matching = tuple(
            item for item in identity_bindings if item.character_id == character_id
        )
        characters = (
            ContinuityCharacterEvidenceDTO(
                character_id=character_id,
                identity_binding=matching[0] if len(matching) == 1 else None,
                costume=_known_text(values.get("costume")),
                emotion=_known_text(values.get("emotion")),
            ),
        )
    props = values.get("props")
    prop_ids = (
        tuple(_logical_value(item) for item in props)
        if isinstance(props, (list, tuple))
        else None
    )
    return PanelContinuityEvidenceDTO(
        page_id=page_id,
        panel_id=_logical_value(values.get("panel_id")),
        storyboard_panel_reference=(
            _logical_value(values.get("storyboard_panel_reference"))
            if values.get("storyboard_panel_reference") is not None
            else None
        ),
        generation_attempt_id=scope.attempt_id if same_generated_page else None,
        generation_output_asset_id=scope.output_asset_id if same_generated_page else None,
        generation_provenance_reference=(
            scope.provenance_reference if same_generated_page else None
        ),
        characters=characters,
        prop_ids=prop_ids,
        location=_known_text(values.get("location")),
        time=_known_text(values.get("time")),
    )


def _explicit_character_id(values: Mapping[object, object]) -> str | None:
    value = values.get("character")
    if value is None:
        return None
    return _logical_value(value)


def _known_text(value: object) -> EvidenceValueDTO | None:
    return EvidenceValueDTO(availability="known", value=value) if isinstance(value, str) else None


def _logical_value(value: object) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or any(character.isspace() for character in value)
        or value.startswith(("/", "\\"))
        or "://" in value
        or "@" in value
    ):
        raise HumanVisualReviewReadinessUnavailable(
            "human visual review readiness is unavailable"
        )
    return value


def _logical_digest_reference(prefix: str, value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True, default=str
    ).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(payload).hexdigest()}"


def build_human_visual_review_readiness(
    repository: LocalFileRepository,
    *,
    page_output_resolver: PageOutputResolverPort | None = None,
) -> HumanVisualReviewReadinessService:
    normal_root = repository._next_generation_normal_execution_owner_root()
    return HumanVisualReviewReadinessService(
        repository,
        SafeLocalGeneratedAssetPresenter(
            ledger_root=repository._workflow_application_ledger_owner_root(),
            evidence_root=normal_root / "evidence",
            asset_root=normal_root / "assets",
        ),
        page_output_resolver,
    )


def attach_human_visual_review_readiness(
    application: object,
    service: HumanVisualReviewReadinessService,
) -> None:
    cast(Any, application)._human_visual_review_readiness = service


def human_visual_review_readiness_for(
    application: object,
) -> HumanVisualReviewReadinessService | None:
    service = getattr(application, "_human_visual_review_readiness", None)
    return service if isinstance(service, HumanVisualReviewReadinessService) else None


__all__ = ()
