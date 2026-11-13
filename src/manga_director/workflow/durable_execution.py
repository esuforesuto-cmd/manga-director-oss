"""Private durable page-execution core for LocalFile composition.

This module is intentionally not a routing entry point.  It provides only the
fenced, revision-aware core that later private CLI/MCP composition may choose
to use.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass, replace
from time import monotonic, sleep
from typing import Any, Literal, Protocol

from manga_director.domain.exceptions import (
    InvalidPageTransition,
    ProjectNotFoundError,
    StateTransitionError,
    ValidationError,
)
from manga_director.domain.project import Project
from manga_director.domain.state_machine import PageState
from manga_director.production.explicit_storyboard_input import (
    _ExplicitStoryboardInputAuthority,
    canonical_json,
    confirmation_record,
    create_authority,
    validate_confirmation,
    validate_expected_source,
    validate_panels,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.local_file_durability import (
    ConditionalCommitResult,
    RevisionedProjectSnapshot,
    _LocalFileProjectAbsentError,
    _R27RevisionPublicationRequest,
)
from manga_director.repositories.project_loader import ProjectLoader
from manga_director.workflow.contracts import WorkflowContext, WorkflowResult, WorkflowStatus
from manga_director.workflow.engine import (
    WorkflowEngine,
    _contains_reserved_storyboard_authority,
    _UnpublishedWorkflowStep,
)
from manga_director.workflow.page_execution_fence import (
    PageExecutionFenceError,
    PageExecutionFencePort,
    WindowsPageExecutionFence,
)

DurableExecutionStatus = Literal[
    "transition_not_applied",
    "transition_applied_event_published",
    "transition_applied_event_failed",
]

_STORYBOARD_CONFIRM_FENCE_WAIT_SECONDS = 30.0
_STORYBOARD_CONFIRM_FENCE_RETRY_SECONDS = 0.025


@dataclass(frozen=True, slots=True)
class DurableWorkflowExecutionResult:
    """Redacted operational result; it never contains a workflow context or event payload."""

    project_id: str
    page_id: str
    status: DurableExecutionStatus
    code: str
    event_published: bool


@dataclass(frozen=True, slots=True)
class _DurableWorkflowExecutionReceipt:
    """Private result retained only by LocalFile delivery routing after CAS."""

    outcome: DurableWorkflowExecutionResult
    workflow_result: WorkflowResult | None = None
    canonical_event: object | None = None
    failure: InvalidPageTransition | None = None
    authoritative_context: WorkflowContext | None = None


class _DurableRoutingError(ValueError):
    """Bounded LocalFile durable-routing failure for internal delivery adapters."""


class _DurableConfirmationNotFoundError(Exception):
    """The initial authoritative Project/Page lookup found no confirmation target."""


class _DurableRunRoutingError(_DurableRoutingError):
    """Bounded failure for a LocalFile durable multi-step CLI run."""


@dataclass(frozen=True, slots=True)
class _R27PublicationIntent:
    """Sealed, process-local handoff for the private R28 test composition."""

    pair: object
    application_binding_identity: str
    attempt_id: str
    project_id: str
    page_id: str
    target_page_reference: str
    source_state: str
    target_state: str
    expected_revision: int
    expected_aggregate_fingerprint: str


class DurablePageStorePort(Protocol):
    """Private authoritative aggregate operations required by the coordinator."""

    def load_revisioned(self, project_id: str) -> RevisionedProjectSnapshot: ...

    def context_from_snapshot(
        self, snapshot: RevisionedProjectSnapshot, page_id: str
    ) -> WorkflowContext: ...

    def project_from_context(
        self,
        snapshot: RevisionedProjectSnapshot,
        page_id: str,
        context: WorkflowContext,
    ) -> Project: ...

    def conditional_commit(
        self, snapshot: RevisionedProjectSnapshot, project: Project
    ) -> ConditionalCommitResult: ...

    def verify_committed(
        self, project_id: str, page_id: str, expected_project: Project
    ) -> bool: ...


class LogicalOutputAssetQualityGatePort(Protocol):
    """Private read-only proof gate for a logical generated artifact."""

    def require_applied(self, context: WorkflowContext) -> str | None: ...


class EvidenceLinkedApprovalProofPort(Protocol):
    """Private retained proof released before the enclosing Page fence."""

    def release(self) -> None: ...


class EvidenceLinkedApprovalGatePort(Protocol):
    """Private in-fence gate for one caller-selected immutable review record."""

    def _prove_under_fence(
        self,
        snapshot: RevisionedProjectSnapshot,
        context: WorkflowContext,
        project_id: str,
        page_id: str,
        review_id: str,
    ) -> EvidenceLinkedApprovalProofPort: ...


@dataclass(frozen=True, slots=True)
class _EvidenceLinkedApprovalAuthority:
    """Process-local marker created only after the private gate succeeds."""

    review_id: str


class LocalFileDurablePageStore(DurablePageStorePort):
    """Private adapter over LocalFile's revision-aware aggregate primitives."""

    def __init__(self, repository: LocalFileRepository, *, _r27_pair: object | None = None) -> None:
        self._repository = repository
        self._r27_pair = _r27_pair
        self._r27_consumed_intents: set[_R27PublicationIntent] = set()

    def load_revisioned(self, project_id: str) -> RevisionedProjectSnapshot:
        return self._repository._load_revisioned(project_id)

    def context_from_snapshot(
        self, snapshot: RevisionedProjectSnapshot, page_id: str
    ) -> WorkflowContext:
        page = snapshot.project.page(_page_number(page_id))
        return ProjectLoader._context_from_page(snapshot.project, page)

    def project_from_context(
        self,
        snapshot: RevisionedProjectSnapshot,
        page_id: str,
        context: WorkflowContext,
    ) -> Project:
        existing_page = snapshot.project.page(_page_number(page_id))
        page = ProjectLoader._page_from_context(existing_page, context)
        return snapshot.project.replace_page(page)

    def conditional_commit(
        self, snapshot: RevisionedProjectSnapshot, project: Project
    ) -> ConditionalCommitResult:
        return self._repository._conditional_commit(snapshot, project)

    def _conditional_commit_r27(
        self,
        snapshot: RevisionedProjectSnapshot,
        project: Project,
        intent: _R27PublicationIntent,
    ) -> ConditionalCommitResult:
        """Consume a private R28 handoff before entering fallible repository work."""

        if type(intent) is not _R27PublicationIntent or intent.pair is not self._r27_pair:
            raise ValueError("r27 publication authority is invalid")
        if intent in self._r27_consumed_intents:
            raise ValueError("r27 publication authority was already consumed")
        if (
            intent.project_id != snapshot.project.id
            or intent.expected_revision != snapshot.revision
            or intent.expected_aggregate_fingerprint != snapshot.fingerprint
        ):
            raise ValueError("r27 publication binding is invalid")
        # Consumption precedes the fallible repository call by contract.
        self._r27_consumed_intents.add(intent)
        request = _R27RevisionPublicationRequest(
            repository_pair=self._repository._r27_repository_pair,
            application_binding_identity=intent.application_binding_identity,
            attempt_id=intent.attempt_id,
            project_id=intent.project_id,
            page_id=intent.page_id,
            target_page_reference=intent.target_page_reference,
            source_state=intent.source_state,
            target_state=intent.target_state,
            expected_revision=intent.expected_revision,
            expected_aggregate_fingerprint=intent.expected_aggregate_fingerprint,
        )
        return self._repository._conditional_commit_r27(snapshot, project, request)

    def _activate_and_conditional_commit_r27(
        self,
        snapshot: RevisionedProjectSnapshot,
        project: Project,
        intent: _R27PublicationIntent,
    ) -> ConditionalCommitResult:
        """Consume one sealed first-activation request before repository work."""

        if type(intent) is not _R27PublicationIntent or intent.pair is not self._r27_pair:
            raise ValueError("r27 publication authority is invalid")
        if intent in self._r27_consumed_intents:
            raise ValueError("r27 publication authority was already consumed")
        if (
            intent.project_id != snapshot.project.id
            or intent.expected_revision != snapshot.revision
            or intent.expected_aggregate_fingerprint != snapshot.fingerprint
        ):
            raise ValueError("r27 publication binding is invalid")
        self._r27_consumed_intents.add(intent)
        request = _R27RevisionPublicationRequest(
            repository_pair=self._repository._r27_repository_pair,
            application_binding_identity=intent.application_binding_identity,
            attempt_id=intent.attempt_id,
            project_id=intent.project_id,
            page_id=intent.page_id,
            target_page_reference=intent.target_page_reference,
            source_state=intent.source_state,
            target_state=intent.target_state,
            expected_revision=intent.expected_revision,
            expected_aggregate_fingerprint=intent.expected_aggregate_fingerprint,
        )
        return self._repository._activate_and_conditional_commit_r27(snapshot, project, request)

    def verify_committed(
        self, project_id: str, page_id: str, expected_project: Project
    ) -> bool:
        verified = self._repository._load_revisioned(project_id).project
        return verified.page(_page_number(page_id)) == expected_project.page(_page_number(page_id))


class DurableWorkflowExecutionCoordinator:
    """Coordinate one ordinary durable primary workflow command without routing activation."""

    def __init__(
        self,
        engine: WorkflowEngine,
        page_store: DurablePageStorePort,
        *,
        fence_factory: Callable[[str, str], PageExecutionFencePort] = WindowsPageExecutionFence,
        logical_output_asset_quality_gate: LogicalOutputAssetQualityGatePort | None = None,
    ) -> None:
        self._engine = engine
        self._page_store = page_store
        self._fence_factory = fence_factory
        self._logical_output_asset_quality_gate = logical_output_asset_quality_gate

    def execute(self, project_id: str, page_id: str, command: str) -> DurableWorkflowExecutionResult:
        """Execute one primary command through the fenced authoritative path exactly once."""

        return self._execute_with_receipt(project_id, page_id, command, {}).outcome

    def _execute_with_receipt(
        self,
        project_id: str,
        page_id: str,
        command: str | None,
        execution_input: Mapping[str, Any],
        *,
        evidence_linked_approval_gate: EvidenceLinkedApprovalGatePort | None = None,
        storyboard_confirmation: Mapping[str, Any] | None = None,
    ) -> _DurableWorkflowExecutionReceipt:
        """Private LocalFile routing seam with an ephemeral command-input overlay."""

        if (
            not _valid_identity(project_id)
            or not _valid_identity(page_id)
            or (command is not None and not _valid_command(command))
        ):
            return _receipt(_not_applied(project_id, page_id, "DURABLE_EXECUTION_INPUT_INVALID"))
        fence: PageExecutionFencePort | None = None
        evidence_proof: EvidenceLinkedApprovalProofPort | None = None
        unpublished: object | None = None
        storyboard_confirmation_present = storyboard_confirmation is not None
        try:
            if storyboard_confirmation_present:
                fence = _acquire_storyboard_confirmation_fence(
                    self._fence_factory, project_id, page_id
                )
            else:
                fence = self._fence_factory(project_id, page_id)
                fence.acquire()
            snapshot = self._load_initial_snapshot(
                project_id,
                storyboard_confirmation_present=storyboard_confirmation is not None,
            )
            context = _context_from_snapshot(
                self._page_store,
                snapshot,
                page_id,
                storyboard_confirmation_present=storyboard_confirmation_present,
            )
            storyboard = context.artifacts.get(PageState.STORYBOARDED.value)
            storyboard_confirmation_present = storyboard_confirmation_present or (
                isinstance(storyboard, Mapping) and "confirmation" in storyboard
            )
            if _contains_reserved_storyboard_authority(context.metadata):
                raise _DurableRoutingError("DURABLE_EXECUTION_INPUT_INVALID")
            command, context = _apply_storyboard_confirmation(
                self._engine,
                snapshot,
                context,
                project_id,
                page_id,
                command,
                storyboard_confirmation,
            )
            command, stop_code = self._command_or_stop(context, command)
            if stop_code is not None:
                return _receipt(
                    _not_applied(project_id, page_id, stop_code),
                    authoritative_context=context,
                )
            assert command is not None
            if command == "prompt":
                _validate_confirmed_storyboard_before_prompt(context, project_id, page_id)
            context, evidence_proof = _prepare_execution_context(
                snapshot,
                context,
                project_id,
                page_id,
                command,
                execution_input,
                evidence_linked_approval_gate,
            )
            unpublished = self._engine._execute_unpublished(context, command=command)
            if not self._engine._is_canonical_unpublished(unpublished):
                self._engine._discard_unpublished(unpublished)
                return _receipt(_not_applied(project_id, page_id, "UNPUBLISHED_EVENT_NONCANONICAL"))
            return self._commit_and_publish(
                snapshot,
                project_id,
                page_id,
                unpublished,
                evidence_proof,
            )
        except Exception as exc:
            if (
                not isinstance(
                    exc,
                    (
                        PageExecutionFenceError,
                        ProjectNotFoundError,
                        _DurableRoutingError,
                        ValidationError,
                        InvalidPageTransition,
                    ),
                )
                and unpublished is not None
                and self._engine._is_canonical_unpublished(unpublished)
            ):
                self._engine._discard_unpublished(unpublished)
            return _execution_failure_receipt(
                exc,
                project_id,
                page_id,
                command,
                storyboard_confirmation,
                storyboard_confirmation_present,
            )
        finally:
            try:
                if evidence_proof is not None:
                    evidence_proof.release()
            finally:
                if fence is not None:
                    fence.release()

    def _load_initial_snapshot(
        self, project_id: str, *, storyboard_confirmation_present: bool
    ) -> RevisionedProjectSnapshot:
        try:
            return self._page_store.load_revisioned(project_id)
        except _LocalFileProjectAbsentError as exc:
            if not storyboard_confirmation_present:
                raise
            raise _DurableConfirmationNotFoundError from exc

    def _commit_and_publish(
        self,
        snapshot: RevisionedProjectSnapshot,
        project_id: str,
        page_id: str,
        unpublished: _UnpublishedWorkflowStep,
        evidence_proof: EvidenceLinkedApprovalProofPort | None,
    ) -> _DurableWorkflowExecutionReceipt:
        next_context = self._engine._unpublished_context(unpublished)
        next_context = _remove_explicit_storyboard_input_authority(next_context)
        if evidence_proof is not None:
            next_context = _remove_evidence_linked_approval_input(next_context)
        project = self._page_store.project_from_context(snapshot, page_id, next_context)
        try:
            self._page_store.conditional_commit(snapshot, project)
        except Exception:
            self._engine._discard_unpublished(unpublished)
            return _receipt(_not_applied(project_id, page_id, "AUTHORITATIVE_CAS_FAILED"))
        try:
            verified = self._page_store.verify_committed(project_id, page_id, project)
        except Exception:
            self._engine._discard_unpublished(unpublished)
            return _receipt(
                _event_failed(project_id, page_id, "AUTHORITATIVE_POST_COMMIT_VERIFICATION_FAILED")
            )
        if not verified:
            self._engine._discard_unpublished(unpublished)
            return _receipt(
                _event_failed(project_id, page_id, "AUTHORITATIVE_POST_COMMIT_VERIFICATION_FAILED")
            )
        safe_result = self._engine._unpublished_result(unpublished).model_copy(
            update={"context": next_context}, deep=False
        )
        safe_unpublished = replace(unpublished, result=safe_result)
        try:
            self._engine._publish_unpublished(safe_unpublished)
        except Exception:
            return _receipt(_event_failed(project_id, page_id, "POST_COMMIT_EVENT_PUBLICATION_FAILED"))
        result = self._engine._unpublished_result(safe_unpublished)
        return _DurableWorkflowExecutionReceipt(
            outcome=DurableWorkflowExecutionResult(
                project_id=project_id,
                page_id=page_id,
                status="transition_applied_event_published",
                code="TRANSITION_APPLIED",
                event_published=True,
            ),
            workflow_result=result,
            canonical_event=result.events[0],
        )

    def _execute_next_with_receipt(
        self, project_id: str, page_id: str
    ) -> _DurableWorkflowExecutionReceipt:
        """Execute one fresh StateMachine-selected step for private CLI run routing."""

        return self._execute_with_receipt(project_id, page_id, None, {})

    def _command_or_stop(
        self, context: WorkflowContext, command: str | None
    ) -> tuple[str | None, str | None]:
        """Derive one run command only from the freshly fenced authoritative context."""

        if command is not None:
            return command, self._quality_gate_stop(context, command)
        if context.state in {PageState.QUALITY_CHECKED, PageState.APPROVED}:
            return None, _run_stop_code(context.state)
        next_command = self._engine._next_command_for_context(context)
        return next_command, self._quality_gate_stop(context, next_command)

    def _quality_gate_stop(self, context: WorkflowContext, command: str) -> str | None:
        """Return a bounded stop code before Quality sees a logical asset."""

        if command != "quality" or not _requires_deferred_logical_output_asset_quality_gating(context):
            return None
        if self._logical_output_asset_quality_gate is None:
            return "LOGICAL_OUTPUT_ASSET_QUALITY_GATING_DEFERRED"
        return self._logical_output_asset_quality_gate.require_applied(context)


def _route_localfile_primary(
    engine: WorkflowEngine,
    repository: LocalFileRepository,
    project_id: str,
    page_id: str,
    command: str,
    execution_input: Mapping[str, Any],
    *,
    logical_output_asset_quality_gate: LogicalOutputAssetQualityGatePort | None = None,
    evidence_linked_approval_gate: EvidenceLinkedApprovalGatePort | None = None,
    storyboard_confirmation: Mapping[str, Any] | None = None,
) -> WorkflowResult:
    """Run one approved LocalFile primary command without a raw-save fallback."""

    receipt = DurableWorkflowExecutionCoordinator(
        engine,
        LocalFileDurablePageStore(repository),
        logical_output_asset_quality_gate=logical_output_asset_quality_gate,
    )._execute_with_receipt(
        project_id,
        page_id,
        command,
        execution_input,
        evidence_linked_approval_gate=evidence_linked_approval_gate,
        storyboard_confirmation=storyboard_confirmation,
    )
    if (
        receipt.outcome.status == "transition_applied_event_published"
        and receipt.workflow_result is not None
        and receipt.canonical_event is receipt.workflow_result.events[0]
    ):
        return receipt.workflow_result
    if receipt.failure is not None:
        raise receipt.failure
    if receipt.outcome.code == "STORYBOARD_CONFIRMATION_CONFLICT":
        raise StateTransitionError("The Reviewed Page changed. Reload it and confirm again.")
    if receipt.outcome.code == "STORYBOARD_CONFIRMATION_NOT_FOUND":
        raise ProjectNotFoundError("The requested Page does not exist.")
    if receipt.outcome.code.startswith("STORYBOARD_CONFIRMATION_"):
        raise ValidationError("Storyboard confirmation is invalid or unsupported.")
    raise _DurableRoutingError(receipt.outcome.code)


def _route_localfile_storyboard_confirmation(
    engine: WorkflowEngine,
    repository: LocalFileRepository,
    project_id: str,
    page_id: str,
    request: Mapping[str, Any],
) -> WorkflowResult:
    """Confirm exact panel intent through the fenced private LocalFile path."""

    receipt = DurableWorkflowExecutionCoordinator(
        engine,
        LocalFileDurablePageStore(repository),
    )._execute_with_receipt(
        project_id,
        page_id,
        "storyboard",
        {},
        storyboard_confirmation=request,
    )
    if (
        receipt.outcome.status == "transition_applied_event_published"
        and receipt.workflow_result is not None
        and receipt.canonical_event is receipt.workflow_result.events[0]
    ):
        return receipt.workflow_result
    if receipt.failure is not None:
        raise receipt.failure
    if receipt.outcome.code == "STORYBOARD_CONFIRMATION_CONFLICT":
        raise StateTransitionError("The Reviewed Page changed. Reload and confirm again.")
    if receipt.outcome.code == "STORYBOARD_CONFIRMATION_NOT_FOUND":
        raise ProjectNotFoundError("The requested Page does not exist.")
    if receipt.outcome.code.startswith("STORYBOARD_CONFIRMATION_"):
        raise ValidationError("Storyboard confirmation is invalid or unsupported.")
    raise _DurableRoutingError(receipt.outcome.code)


def _closed_confirmation_input(request: Mapping[str, Any]) -> None:
    if (
        type(request) is not dict
        or set(request) != {"requestVersion", "expectedSource", "confirmed", "panels"}
        or type(request.get("requestVersion")) is not int
        or request["requestVersion"] != 1
        or type(request.get("confirmed")) is not bool
        or request["confirmed"] is not True
    ):
        raise _DurableRoutingError("STORYBOARD_CONFIRMATION_INVALID")
    validate_expected_source(request["expectedSource"])
    validate_panels(request["panels"])


def _prepare_storyboard_confirmation(
    snapshot: RevisionedProjectSnapshot,
    context: WorkflowContext,
    project_id: str,
    page_id: str,
    request: Mapping[str, Any],
) -> tuple[WorkflowContext, _ExplicitStoryboardInputAuthority]:
    try:
        _closed_confirmation_input(request)
    except ValidationError as exc:
        raise _DurableRoutingError("STORYBOARD_CONFIRMATION_INVALID") from exc
    if (
        context.state is not PageState.REVIEWED
        or type(context.artifacts.get("Designed")) is not dict
        or type(context.artifacts.get("Reviewed")) is not dict
    ):
        raise _DurableRoutingError("STORYBOARD_CONFIRMATION_CONFLICT")
    expected_source = validate_expected_source(request["expectedSource"])
    current_source = {
        "state": "Reviewed",
        "page_design": context.artifacts["Designed"],
        "review": context.artifacts["Reviewed"],
    }
    if canonical_json(expected_source) != canonical_json(current_source):
        raise _DurableRoutingError("STORYBOARD_CONFIRMATION_CONFLICT")
    authority = create_authority(
        project_id,
        _page_number(page_id),
        snapshot.revision,
        snapshot.fingerprint,
        expected_source,
        request["panels"],
    )
    confirmed_context = context.model_copy(
        update={"metadata": {**context.metadata, "_explicit_storyboard_input_authority": authority}},
        deep=False,
    )
    return confirmed_context, authority


def _remove_explicit_storyboard_input_authority(
    context: WorkflowContext,
) -> WorkflowContext:
    metadata = dict(context.metadata)
    metadata.pop("_explicit_storyboard_input_authority", None)
    return context.model_copy(update={"metadata": metadata}, deep=False)


def _preflight_explicit_storyboard(
    engine: WorkflowEngine,
    context: WorkflowContext,
    authority: _ExplicitStoryboardInputAuthority,
) -> None:
    """Use the already configured PromptAgent pipeline before Storyboard mutation."""

    from manga_director.agents.builtin import PromptAgent, StoryboardAgent
    from manga_director.prompting import (
        PromptBuilder,
        PromptOptimizer,
        PromptPipeline,
        PromptRenderer,
        PromptTemplateLoader,
        PromptValidator,
    )

    if type(engine._agents.get(PageState.STORYBOARDED)) is not StoryboardAgent:
        raise _DurableRoutingError("DURABLE_EXECUTION_FAILED")
    prompt_agent = engine._agents.get(PageState.PROMPT_BUILT)
    if type(prompt_agent) is not PromptAgent or "_preflight_explicit_storyboard" in vars(prompt_agent):
        raise _DurableRoutingError("DURABLE_EXECUTION_FAILED")
    pipeline = prompt_agent._pipeline
    if type(pipeline) is not PromptPipeline or any(
        name in vars(pipeline) for name in ("run", "_input_from_context")
    ):
        raise _DurableRoutingError("DURABLE_EXECUTION_FAILED")
    if type(pipeline._template_loader) is not PromptTemplateLoader or any(
        name in vars(pipeline._template_loader) for name in ("load", "_read", "_validate_name")
    ):
        raise _DurableRoutingError("DURABLE_EXECUTION_FAILED")
    pipeline_stages = (
        (pipeline._builder, PromptBuilder, ("build",)),
        (
            pipeline._optimizer,
            PromptOptimizer,
            ("optimize", "_normalize", "_deduplicate", "_provider_directive"),
        ),
        (pipeline._renderer, PromptRenderer, ("render",)),
    )
    if any(
        type(stage) is not stage_type
        or any(method in vars(stage) for method in methods)
        for stage, stage_type, methods in pipeline_stages
    ):
        raise _DurableRoutingError("DURABLE_EXECUTION_FAILED")
    validator = pipeline._validator
    if (
        type(validator) is not PromptValidator
        or type(validator._max_characters) is not int
        or validator._max_characters > 8000
        or any(
            name in vars(validator)
            for name in (
                "validate",
                "_placeholders",
                "_template_variables",
                "_required_template_variables",
            )
        )
    ):
        raise _DurableRoutingError("DURABLE_EXECUTION_FAILED")
    storyboard = {"panels": authority.panels, "confirmation": confirmation_record(authority)}
    artifacts = {**context.artifacts, PageState.STORYBOARDED.value: storyboard}
    candidate = context.model_copy(
        update={"state": PageState.STORYBOARDED, "artifacts": artifacts},
        deep=False,
    )
    candidate = _remove_explicit_storyboard_input_authority(candidate)
    try:
        prompt_agent._preflight_explicit_storyboard(candidate)
    except ValidationError as exc:
        raise _DurableRoutingError("STORYBOARD_CONFIRMATION_INVALID") from exc


def _validate_confirmed_storyboard_before_prompt(
    context: WorkflowContext, project_id: str, page_id: str
) -> None:
    storyboard = context.artifacts.get(PageState.STORYBOARDED.value)
    if isinstance(storyboard, Mapping) and "confirmation" in storyboard:
        validate_confirmation(
            storyboard,
            project_id,
            _page_number(page_id),
            context.artifacts,
        )


def _execution_failure_receipt(
    error: Exception,
    project_id: str,
    page_id: str,
    command: str | None,
    storyboard_confirmation: Mapping[str, Any] | None,
    storyboard_confirmation_present: bool,
) -> _DurableWorkflowExecutionReceipt:
    if isinstance(error, PageExecutionFenceError):
        return _receipt(_not_applied(project_id, page_id, "PAGE_EXECUTION_FENCE_UNAVAILABLE"))
    if isinstance(error, _DurableConfirmationNotFoundError):
        return _receipt(_not_applied(project_id, page_id, "STORYBOARD_CONFIRMATION_NOT_FOUND"))
    if isinstance(error, _DurableRoutingError):
        safe_codes = {
            "DURABLE_EXECUTION_INPUT_INVALID",
            "DURABLE_EXECUTION_INPUT_CONFLICT",
        }
        code = (
            str(error)
            if str(error).startswith("STORYBOARD_CONFIRMATION_") or str(error) in safe_codes
            else "DURABLE_EXECUTION_FAILED"
        )
        return _receipt(_not_applied(project_id, page_id, code))
    if isinstance(error, ValidationError):
        code = (
            "STORYBOARD_CONFIRMATION_INVALID"
            if command == "prompt" and storyboard_confirmation_present
            else "DURABLE_EXECUTION_FAILED"
        )
        return _receipt(_not_applied(project_id, page_id, code))
    if isinstance(error, InvalidPageTransition):
        return _receipt(
            _not_applied(project_id, page_id, "DURABLE_EXECUTION_FAILED"), failure=error
        )
    return _receipt(_not_applied(project_id, page_id, "DURABLE_EXECUTION_FAILED"))


def _acquire_storyboard_confirmation_fence(
    fence_factory: Callable[[str, str], PageExecutionFencePort],
    project_id: str,
    page_id: str,
) -> PageExecutionFencePort:
    """Wait briefly for a competing confirmation before reading Page state."""

    deadline = monotonic() + _STORYBOARD_CONFIRM_FENCE_WAIT_SECONDS
    while True:
        fence = fence_factory(project_id, page_id)
        try:
            fence.acquire()
            return fence
        except PageExecutionFenceError as error:
            if str(error) != "page_execution_fence_contended":
                raise
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise
            sleep(min(_STORYBOARD_CONFIRM_FENCE_RETRY_SECONDS, remaining))


def _context_from_snapshot(
    page_store: DurablePageStorePort,
    snapshot: RevisionedProjectSnapshot,
    page_id: str,
    *,
    storyboard_confirmation_present: bool,
) -> WorkflowContext:
    try:
        page = snapshot.project.page(_page_number(page_id))
        if _contains_reserved_storyboard_authority(page.metadata):
            raise _DurableRoutingError("DURABLE_EXECUTION_INPUT_INVALID")
        return page_store.context_from_snapshot(snapshot, page_id)
    except ProjectNotFoundError as exc:
        if not storyboard_confirmation_present:
            raise
        raise _DurableConfirmationNotFoundError from exc


def _apply_storyboard_confirmation(
    engine: WorkflowEngine,
    snapshot: RevisionedProjectSnapshot,
    context: WorkflowContext,
    project_id: str,
    page_id: str,
    command: str | None,
    storyboard_confirmation: Mapping[str, Any] | None,
) -> tuple[str | None, WorkflowContext]:
    if storyboard_confirmation is None:
        return command, context
    context, authority = _prepare_storyboard_confirmation(
        snapshot,
        context,
        project_id,
        page_id,
        storyboard_confirmation,
    )
    _preflight_explicit_storyboard(engine, context, authority)
    return "storyboard", context


def _route_localfile_run(
    engine: WorkflowEngine,
    repository: LocalFileRepository,
    project_id: str,
    page_id: str,
    *,
    fence_factory: Callable[[str, str], PageExecutionFencePort] = WindowsPageExecutionFence,
    logical_output_asset_quality_gate: LogicalOutputAssetQualityGatePort | None = None,
) -> WorkflowResult | WorkflowStatus:
    """Run LocalFile primary transitions one fresh durable step at a time."""

    coordinator = DurableWorkflowExecutionCoordinator(
        engine,
        LocalFileDurablePageStore(repository),
        fence_factory=fence_factory,
        logical_output_asset_quality_gate=logical_output_asset_quality_gate,
    )
    successful: list[_DurableWorkflowExecutionReceipt] = []
    while True:
        receipt = coordinator._execute_next_with_receipt(project_id, page_id)
        if receipt.outcome.status == "transition_applied_event_published":
            if receipt.workflow_result is None or receipt.canonical_event is not receipt.workflow_result.events[0]:
                raise _DurableRunRoutingError("DURABLE_RUN_RECEIPT_INVALID")
            successful.append(receipt)
            continue
        if receipt.outcome.code in {"RUN_STOP_QUALITY_CHECKED", "RUN_STOP_APPROVED"}:
            if successful:
                result = successful[-1].workflow_result
                if result is None:
                    raise _DurableRunRoutingError("DURABLE_RUN_RECEIPT_INVALID")
                return result
            if receipt.authoritative_context is None:
                raise _DurableRunRoutingError("DURABLE_RUN_STOP_CONTEXT_MISSING")
            return engine.status(receipt.authoritative_context)
        prefix = "DURABLE_RUN_PARTIAL_PROGRESS" if successful else "DURABLE_RUN_NOT_APPLIED"
        raise _DurableRunRoutingError(f"{prefix}:{receipt.outcome.code}")


def _not_applied(project_id: str, page_id: str, code: str) -> DurableWorkflowExecutionResult:
    return DurableWorkflowExecutionResult(
        project_id=project_id,
        page_id=page_id,
        status="transition_not_applied",
        code=code,
        event_published=False,
    )


def _event_failed(project_id: str, page_id: str, code: str) -> DurableWorkflowExecutionResult:
    return DurableWorkflowExecutionResult(
        project_id=project_id,
        page_id=page_id,
        status="transition_applied_event_failed",
        code=code,
        event_published=False,
    )


def _receipt(
    outcome: DurableWorkflowExecutionResult,
    *,
    failure: InvalidPageTransition | None = None,
    authoritative_context: WorkflowContext | None = None,
) -> _DurableWorkflowExecutionReceipt:
    return _DurableWorkflowExecutionReceipt(
        outcome=outcome,
        failure=failure,
        authoritative_context=authoritative_context,
    )


def _run_stop_code(state: PageState) -> str:
    if state == PageState.QUALITY_CHECKED:
        return "RUN_STOP_QUALITY_CHECKED"
    return "RUN_STOP_APPROVED"


def _requires_deferred_logical_output_asset_quality_gating(context: WorkflowContext) -> bool:
    if context.state != PageState.GENERATED:
        return False
    image = context.artifacts.get(PageState.GENERATED.value)
    return (
        isinstance(image, Mapping)
        and image.get("artifact_kind") == "logical_output_asset"
        and isinstance(image.get("output_asset_id"), str)
        and bool(image["output_asset_id"].strip())
    )


_COMMAND_OVERLAY_KEYS: dict[str, frozenset[str]] = {
    "design": frozenset({"page_design"}),
    "quality": frozenset({"quality_scores"}),
    "approve": frozenset({"approved_by"}),
    "review": frozenset(),
    "storyboard": frozenset(),
    "prompt": frozenset(),
    "generate": frozenset(),
}
_PAGE_DESIGN_KEYS = frozenset(
    {
        "panel_count",
        "panel_roles",
        "page_type",
        "purpose",
        "reader_emotion",
        "featured_character",
        "big_moment",
        "hook",
    }
)
_QUALITY_CRITERIA = frozenset(
    {
        "composition",
        "direction",
        "background",
        "character_fidelity",
        "dialogue",
        "eye_flow",
        "tempo",
        "page_purpose",
        "hook",
    }
)


def _apply_execution_input(
    context: WorkflowContext, command: str, execution_input: Mapping[str, Any]
) -> WorkflowContext:
    """Apply the closed, command-scoped overlay to a freshly loaded context only."""

    if command not in _COMMAND_OVERLAY_KEYS or not isinstance(execution_input, Mapping):
        raise _DurableRoutingError("DURABLE_EXECUTION_INPUT_INVALID")
    if command == "approve" and "review_evidence_id" in execution_input:
        raise _DurableRoutingError("DURABLE_EXECUTION_FAILED")
    values = dict(execution_input)
    allowed = _COMMAND_OVERLAY_KEYS[command]
    if set(values) - allowed:
        raise _DurableRoutingError("DURABLE_EXECUTION_INPUT_INVALID")
    if not values:
        return context
    if any(key in context.metadata and context.metadata[key] != value for key, value in values.items()):
        raise _DurableRoutingError("DURABLE_EXECUTION_INPUT_CONFLICT")
    if command == "design":
        _validate_page_design(values)
    elif command == "quality":
        _validate_quality_scores(values)
    elif command == "approve":
        _validate_approved_by(values)
    return context.model_copy(
        update={"metadata": {**deepcopy(context.metadata), **deepcopy(values)}},
        deep=True,
    )


def _prepare_execution_context(
    snapshot: RevisionedProjectSnapshot,
    context: WorkflowContext,
    project_id: str,
    page_id: str,
    command: str,
    execution_input: Mapping[str, Any],
    evidence_linked_approval_gate: EvidenceLinkedApprovalGatePort | None,
) -> tuple[WorkflowContext, EvidenceLinkedApprovalProofPort | None]:
    if evidence_linked_approval_gate is None:
        return _apply_execution_input(context, command, execution_input), None
    approved_by, review_id = _validated_evidence_linked_approval_input(
        command,
        execution_input,
        context,
    )
    proof = evidence_linked_approval_gate._prove_under_fence(
        snapshot,
        context,
        project_id,
        page_id,
        review_id,
    )
    try:
        return _apply_evidence_linked_approval_input(context, approved_by, review_id), proof
    except Exception:
        proof.release()
        raise


def _validate_page_design(values: dict[str, Any]) -> None:
    if set(values) != {"page_design"} or not isinstance(values["page_design"], Mapping):
        raise _DurableRoutingError("DURABLE_EXECUTION_INPUT_INVALID")
    design = values["page_design"]
    if set(design) - _PAGE_DESIGN_KEYS:
        raise _DurableRoutingError("DURABLE_EXECUTION_INPUT_INVALID")
    if "panel_count" in design and (
        isinstance(design["panel_count"], bool) or not isinstance(design["panel_count"], int)
    ):
        raise _DurableRoutingError("DURABLE_EXECUTION_INPUT_INVALID")
    if "panel_roles" in design and (
        not isinstance(design["panel_roles"], (list, tuple))
        or not all(isinstance(role, str) for role in design["panel_roles"])
    ):
        raise _DurableRoutingError("DURABLE_EXECUTION_INPUT_INVALID")
    text_keys = _PAGE_DESIGN_KEYS - {"panel_count", "panel_roles"}
    if any(key in design and not isinstance(design[key], str) for key in text_keys):
        raise _DurableRoutingError("DURABLE_EXECUTION_INPUT_INVALID")


def _validate_quality_scores(values: dict[str, Any]) -> None:
    if set(values) != {"quality_scores"} or not isinstance(values["quality_scores"], Mapping):
        raise _DurableRoutingError("DURABLE_EXECUTION_INPUT_INVALID")
    scores = values["quality_scores"]
    if set(scores) - _QUALITY_CRITERIA or any(
        isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 5
        for score in scores.values()
    ):
        raise _DurableRoutingError("DURABLE_EXECUTION_INPUT_INVALID")


def _validate_approved_by(values: dict[str, Any]) -> None:
    approved_by = values.get("approved_by")
    if set(values) != {"approved_by"} or not isinstance(approved_by, str) or not approved_by.strip():
        raise _DurableRoutingError("DURABLE_EXECUTION_INPUT_INVALID")


def _validated_evidence_linked_approval_input(
    command: str,
    execution_input: Mapping[str, Any],
    context: WorkflowContext,
) -> tuple[str, str]:
    values = dict(execution_input)
    approved_by = values.get("approved_by")
    review_id = values.get("review_evidence_id")
    if (
        command != "approve"
        or set(values) != {"approved_by", "review_evidence_id"}
        or not _valid_bounded_reference(approved_by)
        or not _valid_bounded_reference(review_id)
        or "review_evidence_id" in context.metadata
        or "_evidence_linked_approval_authority" in context.metadata
    ):
        raise _DurableRoutingError("DURABLE_EXECUTION_INPUT_INVALID")
    assert isinstance(approved_by, str)
    assert isinstance(review_id, str)
    return approved_by, review_id


def _apply_evidence_linked_approval_input(
    context: WorkflowContext,
    approved_by: str,
    review_id: str,
) -> WorkflowContext:
    return context.model_copy(
        update={
            "metadata": {
                **deepcopy(context.metadata),
                "approved_by": approved_by,
                "review_evidence_id": review_id,
                "_evidence_linked_approval_authority": _EvidenceLinkedApprovalAuthority(
                    review_id
                ),
            }
        },
        deep=False,
    )


def _remove_evidence_linked_approval_input(
    context: WorkflowContext,
) -> WorkflowContext:
    metadata = dict(context.metadata)
    metadata.pop("review_evidence_id", None)
    metadata.pop("_evidence_linked_approval_authority", None)
    return context.model_copy(update={"metadata": metadata}, deep=False)


def _valid_bounded_reference(value: object) -> bool:
    return bool(
        isinstance(value, str)
        and 1 <= len(value) <= 200
        and value == value.strip()
        and not any(character.isspace() or ord(character) < 32 for character in value)
        and not value.startswith(("/", "\\"))
        and "/" not in value
        and "\\" not in value
        and "://" not in value
        and "@" not in value
    )


def _page_number(page_id: str) -> int:
    if not page_id.isdecimal() or int(page_id) < 1:
        raise ValueError("page identifier is invalid")
    return int(page_id)


def _valid_identity(value: str) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and value == value.strip()
        and not value.startswith(("/", "\\"))
        and "://" not in value
        and "@" not in value
    )


def _valid_command(value: str) -> bool:
    return isinstance(value, str) and bool(value) and value == value.strip()
