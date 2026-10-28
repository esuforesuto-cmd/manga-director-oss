"""Private Slice 1 composition for LocalFile panel-aware generation."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, Protocol

from manga_director.domain.state_machine import PageState
from manga_director.production.next_generation_authorized_execution_envelope import (
    AuthorizedGenerationExecutionEnvelopeDTO,
    AuthorizedGenerationExecutionEnvelopeValidationService,
)
from manga_director.production.next_generation_comfyui_fixed_workflow import (
    validate_comfyui_checkpoint_name,
)
from manga_director.production.next_generation_comfyui_provider_adapter import (
    ComfyUIHttpClientPort,
)
from manga_director.production.next_generation_deterministic_composite_asset_owner import (
    DeterministicCompositeAssetOwner,
)
from manga_director.production.next_generation_execution_authorization import (
    ExecutionAuthorizationRecordDTO,
    ExecutionAuthorizationValidationService,
)
from manga_director.production.next_generation_generation_evidence import (
    EvidenceValueDTO,
    GenerationInputEvidenceDTO,
)
from manga_director.production.next_generation_page_composition import (
    LocalPageCompositionAuthority,
)
from manga_director.production.next_generation_page_composition_application_ledger import (
    LocalPageCompositionApplicationLedger,
    PageCompositionApplicationBinding,
)
from manga_director.production.next_generation_page_generation_mode_claim import (
    LocalPageGenerationModeClaimStore,
    PageGenerationModeClaim,
)
from manga_director.production.next_generation_page_generation_plan import PanelRectangle
from manga_director.production.next_generation_page_output_proof import (
    DeterministicCompositionPageOutputProof,
)
from manga_director.production.next_generation_panel_execution_attempt import (
    PanelAttemptReservation,
    PanelGenerationRequest,
)
from manga_director.production.next_generation_panel_generation_evidence import (
    LocalPanelGenerationAuthority,
)
from manga_director.production.next_generation_pre_execution_readiness import (
    PreExecutionReadinessInputDTO,
    PreExecutionReadinessService,
)
from manga_director.production.next_generation_provider_capability_negotiation import (
    GenerationCapabilityRequirementDTO,
    ProviderCapabilityDeclarationDTO,
    ProviderCapabilityNegotiationService,
    ProviderCapabilityStateDTO,
)
from manga_director.production.next_generation_provider_configuration import (
    AuthoritativeProviderConfigurationSnapshot,
    ProviderConfigurationNormalizationService,
)
from manga_director.production.next_generation_provider_output_configuration import (
    ProviderOutputConfigurationBindingDTO,
    ProviderOutputConfigurationBindingReport,
)
from manga_director.production.next_generation_structured_generation_request import (
    GenerationProductionProfileDTO,
    StructuredGenerationRequestDTO,
    StructuredGenerationRequestValidationService,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow.contracts import AgentResult
from manga_director.workflow.durable_execution import (
    DurableWorkflowExecutionCoordinator,
    LocalFileDurablePageStore,
)
from manga_director.workflow.engine import WorkflowEngine
from manga_director.workflow.localfile_comfyui_panel_provider import (
    LocalFileComfyUIPanelProvider,
    TransportFactory,
)
from manga_director.workflow.localfile_page_generation_mode_admission import (
    LocalFilePageGenerationModeAdmission,
    LocalFilePageGenerationModeObservation,
)
from manga_director.workflow.localfile_panel_aware_activation_bridge import (
    _build_panel_aware_page_generation_operation,
    _convert_revisioned_page_snapshot,
    _snapshot_page_binding,
)
from manga_director.workflow.localfile_panel_aware_page_generation import (
    LocalFilePanelAwarePageGeneration,
)
from manga_director.workflow.page_execution_fence import (
    PageExecutionFencePort,
    local_page_execution_fence,
)

_PROVIDER_REFERENCE = "provider-comfyui-v7-014"
_PROVIDER_ID = "comfyui"
_PROFILE_ID = "profile:v7-04:prompt-only-png"
_PROFILE_VERSION = "v1"
_WORKFLOW_ID = "workflow:v7-04:fixed-core-png"
_WORKFLOW_VERSION = "v1"
_MODEL_VERSION = "local-checkpoint"
_OUTPUT_SIZE = "1024x1024"
_OUTPUT_QUALITY = "medium"
_LAYOUT_PROFILE_ID = "md-page-compositor-v1"
_LAYOUT_PROFILE_VERSION = 1
_HUMAN_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_GENERIC_HUMAN_IDENTITIES = frozenset(
    {"anonymous", "default", "local-user", "system", "unknown", "user"}
)
_UNSAFE_IDENTITY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "endpoint",
    "password",
    "secret",
    "token",
)
_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[\\/]")


@dataclass(frozen=True, slots=True)
class LocalFilePanelAwareActivationResult:
    """Bounded private activation outcome; it contains no private IDs."""

    status: Literal["generated", "partial", "blocked", "recovery_required"]
    code: str
    provider_calls: int = 0


class _FenceFactory(Protocol):
    def __call__(self, project_id: str, page_id: str) -> PageExecutionFencePort: ...


def execute_localfile_panel_aware_generation(
    repository: LocalFileRepository,
    engine: WorkflowEngine,
    project_id: str,
    page_number: int,
    authorized_by: str,
    checkpoint_name: str,
    rectangles: tuple[PanelRectangle, ...],
    *,
    layout_profile_id: str = _LAYOUT_PROFILE_ID,
    layout_profile_version: int = _LAYOUT_PROFILE_VERSION,
    http_client: ComfyUIHttpClientPort | None = None,
    transport_factory: TransportFactory | None = None,
    now: Callable[[], datetime] | None = None,
    fence_factory: _FenceFactory = local_page_execution_fence,
) -> LocalFilePanelAwareActivationResult:
    """Run one exact PromptBuilt activation through existing private authorities."""

    if type(repository) is not LocalFileRepository or not isinstance(engine, WorkflowEngine):
        return _blocked("activation_unavailable")
    if type(project_id) is not str or not project_id or project_id != project_id.strip():
        return _blocked("activation_input_invalid")
    if type(page_number) is not int or page_number < 1:
        return _blocked("activation_input_invalid")
    if not _valid_human_identity(authorized_by):
        return _blocked("activation_input_invalid")
    try:
        checkpoint = validate_comfyui_checkpoint_name(checkpoint_name)
        observed_at = (now or (lambda: datetime.now(UTC)))()
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            return _blocked("activation_input_invalid")
        fence = fence_factory(project_id, str(page_number))
        fence.acquire()
        try:
            snapshot = repository._load_revisioned(project_id)
            observed_page = snapshot.project.page(page_number)
            if observed_page.state != PageState.PROMPT_BUILT:
                return _blocked("revision_conflict")
            binding = _snapshot_page_binding(snapshot, page_number)
        finally:
            fence.release()
        bound_project_id, page_id, _, page_revision, page_fingerprint, page = binding
        if bound_project_id != project_id or page.state != PageState.PROMPT_BUILT:
            return _blocked("revision_conflict")
        conversion = _convert_revisioned_page_snapshot(
            repository,
            snapshot,
            page_number=page_number,
            layout_profile_id=layout_profile_id,
            layout_profile_version=layout_profile_version,
            rectangles=rectangles,
        )
        activation_binding = _activation_binding(
            project_id=project_id,
            page_id=page_id,
            page_revision=page_revision,
            page_fingerprint=page_fingerprint,
            plan_id=conversion.plan.plan_id,
            checkpoint_name=checkpoint,
            authorized_by=authorized_by,
            layout_profile_id=layout_profile_id,
            layout_profile_version=layout_profile_version,
            rectangles=rectangles,
        )
        activation_sha256 = _sha256(_canonical_json(activation_binding).encode("utf-8"))
        mode_claim = PageGenerationModeClaim(
            claim_id=f"claim-v7-015-{activation_sha256}",
            project_id=project_id,
            page_id=page_id,
            page_revision=page_revision,
            page_fingerprint=page_fingerprint,
            mode="panel_aware",
            mode_binding_reference=conversion.plan.plan_id,
            authorizer_reference=f"mode-authorizer-v7-015-{activation_sha256}",
        )
        authorization_references = tuple(
            _stable_reference(
                "authorization-v7-015-",
                {
                    "kind": "panel_authorization_v1",
                    "activation_sha256": activation_sha256,
                    "panel_id": panel.panel_id,
                    "panel_order": panel.order,
                },
            )
            for panel in conversion.plan.panels
        )
        composition_authorization_reference = _stable_reference(
            "composition-authorization-v7-015-",
            {"kind": "composition_authorization_v1", "activation_sha256": activation_sha256},
        )
        operation = _build_panel_aware_page_generation_operation(
            repository,
            snapshot,
            page_number=page_number,
            layout_profile_id=layout_profile_id,
            layout_profile_version=layout_profile_version,
            rectangles=rectangles,
            mode_claim=mode_claim,
            authorization_references=authorization_references,
            composition_authorization_reference=composition_authorization_reference,
            checkpoint_name=checkpoint,
        )
        owner_root = repository._next_generation_normal_execution_owner_root()
        observation = LocalFilePageGenerationModeObservation(repository)
        admission = LocalFilePageGenerationModeAdmission(
            LocalPageGenerationModeClaimStore(observation.claim_root), observation
        )
        config_factory = _configuration_factory(authorized_by, observed_at, activation_sha256)
        provider = LocalFileComfyUIPanelProvider(
            checkpoint_name=checkpoint,
            owner_root=owner_root / "assets",
            configuration_report_factory=config_factory,
            http_client=http_client,
            transport_factory=transport_factory,
        )
        admission_fence = fence_factory(project_id, page_id)
        application = _SafeGeneratedPageApplication(repository, engine, admission_fence)
        orchestrator = LocalFilePanelAwarePageGeneration(
            mode_admission=admission,
            panel_authority=LocalPanelGenerationAuthority(
                owner_root / "panel-generation-authority"
            ),
            provider=provider,
            panel_reader=provider,
            composition_authority=LocalPageCompositionAuthority(
                owner_root / "page-composition-authority"
            ),
            composite_owner=DeterministicCompositeAssetOwner(
                owner_root / "deterministic-composite-owner"
            ),
            application_ledger=LocalPageCompositionApplicationLedger(
                owner_root / "page-composition-application"
            ),
            generate_command=application,
        )
        result = orchestrator.execute(operation, admission_fence=admission_fence)
        return LocalFilePanelAwareActivationResult(
            status=result.status, code=result.code, provider_calls=result.provider_calls
        )
    except Exception:
        return _blocked("activation_unavailable")


def _configuration_factory(
    authorized_by: str,
    authorized_at: datetime,
    activation_sha256: str,
) -> Callable[
    [PanelGenerationRequest, PanelAttemptReservation, str],
    ProviderOutputConfigurationBindingReport | None,
]:
    def build(
        request: PanelGenerationRequest,
        reservation: PanelAttemptReservation,
        checkpoint_name: str,
    ) -> ProviderOutputConfigurationBindingReport | None:
        try:
            requirements = (
                GenerationCapabilityRequirementDTO(
                    capability_id="text_prompt", requirement_level="required"
                ),
                GenerationCapabilityRequirementDTO(
                    capability_id="output_format", requirement_level="required"
                ),
            )
            profile = GenerationProductionProfileDTO(
                profile_id=_PROFILE_ID,
                profile_version=_PROFILE_VERSION,
                capability_requirements=requirements,
            )
            target_reference = f"page.{request.project_id}.{request.page_id}"
            intent_reference = f"intent:v7-15:{activation_sha256}"
            structured = StructuredGenerationRequestValidationService().validate(
                StructuredGenerationRequestDTO(
                    request_id=request.request_id,
                    target_page_reference=target_reference,
                    target_panel_reference=request.panel_id,
                    generation_intent_reference=intent_reference,
                    input=GenerationInputEvidenceDTO(
                        input_reference=request.input_reference,
                        input_content_hash=EvidenceValueDTO(
                            availability="known", value=request.input_sha256
                        ),
                    ),
                    capability_requirements=requirements,
                    provenance_reference=request.provenance_reference,
                    profile_id=_PROFILE_ID,
                    profile_version=_PROFILE_VERSION,
                ),
                profile,
            )
            capability = ProviderCapabilityNegotiationService().validate(
                requirements,
                ProviderCapabilityDeclarationDTO(
                    provider_reference=_PROVIDER_REFERENCE,
                    capability_states=(
                        ProviderCapabilityStateDTO(capability_id="text_prompt", state="supported"),
                        ProviderCapabilityStateDTO(
                            capability_id="output_format", state="supported"
                        ),
                    ),
                ),
            )
            readiness = PreExecutionReadinessService().validate(
                PreExecutionReadinessInputDTO(
                    request_validation_report=structured,
                    capability_negotiation_report=capability,
                    provider_reference=_PROVIDER_REFERENCE,
                )
            )
            execution = ExecutionAuthorizationValidationService().validate(
                readiness,
                (
                    ExecutionAuthorizationRecordDTO(
                        authorization_id=reservation.authorization_reference,
                        authorizer_id=authorized_by,
                        authorized_at=authorized_at,
                        request_id=request.request_id,
                        provider_reference=_PROVIDER_REFERENCE,
                    ),
                ),
            )
            envelope = AuthorizedGenerationExecutionEnvelopeValidationService().validate(
                (
                    AuthorizedGenerationExecutionEnvelopeDTO(
                        attempt_id=reservation.attempt_id,
                        request_id=request.request_id,
                        provider_reference=_PROVIDER_REFERENCE,
                        authorization_ids=(reservation.authorization_reference,),
                        profile_id=_PROFILE_ID,
                        profile_version=_PROFILE_VERSION,
                        generation_intent_reference=intent_reference,
                        input_reference=request.input_reference,
                    ),
                ),
                execution,
            )
            configuration = ProviderConfigurationNormalizationService().normalize(
                reservation.attempt_id,
                AuthoritativeProviderConfigurationSnapshot(
                    attempt_id=reservation.attempt_id,
                    provider_reference=_PROVIDER_REFERENCE,
                    profile_id=_PROFILE_ID,
                    profile_version=_PROFILE_VERSION,
                    provider_id=EvidenceValueDTO(availability="known", value=_PROVIDER_ID),
                    model_id=EvidenceValueDTO(availability="known", value=checkpoint_name),
                    model_version=EvidenceValueDTO(availability="known", value=_MODEL_VERSION),
                    workflow_id=EvidenceValueDTO(availability="known", value=_WORKFLOW_ID),
                    workflow_version=EvidenceValueDTO(
                        availability="known", value=_WORKFLOW_VERSION
                    ),
                    requested_seed=EvidenceValueDTO(
                        availability="known", value="derived-from-attempt"
                    ),
                ),
                envelope,
            )
            if not all(
                (
                    structured.ready,
                    capability.ready,
                    readiness.ready,
                    execution.ready,
                    envelope.ready,
                    configuration.ready,
                )
            ):
                return None
            # V7-04's ComfyUI transport consumes this bounded report. The generic
            # output-binding service only accepts OpenAI; preserve V7-04's existing
            # explicit ComfyUI binding contract without changing that authority.
            output = ProviderOutputConfigurationBindingDTO(
                attempt_id=reservation.attempt_id,
                provider_reference=_PROVIDER_REFERENCE,
                profile_id=_PROFILE_ID,
                profile_version=_PROFILE_VERSION,
                model_id=checkpoint_name,
                output_size=_OUTPUT_SIZE,
                output_quality=_OUTPUT_QUALITY,
            )
            return ProviderOutputConfigurationBindingReport(
                provider_configuration_normalization_report=configuration,
                output_configuration=output,
                findings=(),
                status="ready",
                ready=True,
            )
        except (TypeError, ValueError):
            return None

    return build


class _SafeGeneratedPageApplication:
    """Apply one exact composition proof through the existing durable command path."""

    def __init__(
        self,
        repository: LocalFileRepository,
        engine: WorkflowEngine,
        admission_fence: PageExecutionFencePort,
    ) -> None:
        self._repository = repository
        self._engine = engine
        self._admission_fence = admission_fence

    def generate(
        self,
        binding: PageCompositionApplicationBinding,
        proof: DeterministicCompositionPageOutputProof,
    ) -> bool:
        if not _binding_matches_proof(binding, proof):
            return False
        try:
            snapshot = self._repository._load_revisioned(binding.project_id)
            if f"revision-{snapshot.revision}" != binding.page_revision:
                return False
            page = snapshot.project.page(int(binding.page_id))
            if page.state != PageState.PROMPT_BUILT:
                return False
            workflow = dict(self._engine._agents)
            workflow[PageState.GENERATED] = _ProofBoundGenerationAgent(binding, proof)
            safe_engine = WorkflowEngine(
                state_machine=self._engine._state_machine,
                event_bus=self._engine._event_bus,
                agents=workflow,
                support_agents=self._engine._support_agents,
                observer=self._engine._observer,
            )
            borrowed = _BorrowedFence(self._admission_fence)
            coordinator = DurableWorkflowExecutionCoordinator(
                safe_engine,
                LocalFileDurablePageStore(self._repository),
                fence_factory=lambda _project_id, _page_id: borrowed,
            )
            result = coordinator.execute(binding.project_id, binding.page_id, "generate")
            return result.status == "transition_applied_event_published" and result.event_published
        except (TypeError, ValueError, OSError):
            return False


class _ProofBoundGenerationAgent:
    def __init__(
        self,
        binding: PageCompositionApplicationBinding,
        proof: DeterministicCompositionPageOutputProof,
    ) -> None:
        self._binding = binding
        self._proof = proof

    def execute(self, context: object) -> AgentResult:
        if not _binding_matches_proof(self._binding, self._proof):
            return AgentResult(success=False, state=PageState.GENERATED)
        if getattr(context, "state", None) != PageState.PROMPT_BUILT:
            return AgentResult(success=False, state=PageState.GENERATED)
        return AgentResult(
            success=True,
            state=PageState.GENERATED,
            payload={
                "artifact_kind": "logical_output_asset",
                "output_asset_id": self._binding.composite_asset_id,
            },
        )


class _BorrowedFence:
    def __init__(self, fence: PageExecutionFencePort) -> None:
        self._fence = fence

    def acquire(self) -> None:
        return None

    def release(self) -> None:
        return None

    def _r26_is_held_for(self, project_id: str, page_id: str) -> bool:
        check = getattr(self._fence, "_r26_is_held_for", None)
        return bool(callable(check) and check(project_id, page_id))


def _binding_matches_proof(
    binding: PageCompositionApplicationBinding,
    proof: DeterministicCompositionPageOutputProof,
) -> bool:
    return bool(
        type(binding) is PageCompositionApplicationBinding
        and type(proof) is DeterministicCompositionPageOutputProof
        and binding.project_id == proof.project_id
        and binding.page_id == proof.page_id
        and proof.target_page_reference == f"page.{binding.project_id}.{binding.page_id}"
        and binding.composition_attempt_id == proof.attempt_id
        and binding.composition_provenance_reference == proof.provenance_reference
        and binding.composite_asset_id == proof.asset_id
        and binding.composite_sha256 == proof.content_sha256
        and binding.plan_id == proof.plan_id
        and binding.plan_fingerprint == proof.plan_fingerprint
        and binding.request_fingerprint == proof.request_fingerprint
        and binding.evidence_id == proof.evidence_id
        and binding.evidence_sha256 == proof.evidence_sha256
    )


def _activation_binding(
    *,
    project_id: str,
    page_id: str,
    page_revision: str,
    page_fingerprint: str,
    plan_id: str,
    checkpoint_name: str,
    authorized_by: str,
    layout_profile_id: str,
    layout_profile_version: int,
    rectangles: tuple[PanelRectangle, ...],
) -> dict[str, object]:
    return {
        "kind": "panel_aware_activation_v1",
        "version": 1,
        "project_id": project_id,
        "page_id": page_id,
        "page_revision": page_revision,
        "page_fingerprint": page_fingerprint,
        "plan_id": plan_id,
        "checkpoint_name": checkpoint_name,
        "authorized_by": authorized_by,
        "layout_profile_id": layout_profile_id,
        "layout_profile_version": layout_profile_version,
        "rectangles": [rectangle.model_dump(mode="json") for rectangle in rectangles],
    }


def _stable_reference(prefix: str, value: Mapping[str, object]) -> str:
    return f"{prefix}{_sha256(_canonical_json(value).encode('utf-8'))}"


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _valid_human_identity(value: object) -> bool:
    if not isinstance(value, str) or not _HUMAN_IDENTITY.fullmatch(value):
        return False
    lowered = value.lower()
    return (
        lowered not in _GENERIC_HUMAN_IDENTITIES
        and not any(marker in lowered for marker in _UNSAFE_IDENTITY_PARTS)
        and "@" not in value
        and not _WINDOWS_ABSOLUTE_PATH.match(value)
    )


def _blocked(code: str) -> LocalFilePanelAwareActivationResult:
    return LocalFilePanelAwareActivationResult("blocked", code)
