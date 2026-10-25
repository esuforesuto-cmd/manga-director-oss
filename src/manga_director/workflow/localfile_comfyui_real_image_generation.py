"""Private LocalFile composition for one explicitly authorized ComfyUI attempt."""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from manga_director.domain.state_machine import PageState
from manga_director.production.next_generation_authorized_execution_envelope import (
    AuthorizedGenerationExecutionEnvelopeDTO,
    AuthorizedGenerationExecutionEnvelopeValidationReport,
    AuthorizedGenerationExecutionEnvelopeValidationService,
)
from manga_director.production.next_generation_comfyui_fixed_workflow import (
    validate_comfyui_checkpoint_name,
)
from manga_director.production.next_generation_comfyui_output_asset_registration import (
    ComfyUIAssetOwnerSinkBridge,
    ComfyUIOutputAssetRegistrationAdapter,
)
from manga_director.production.next_generation_comfyui_provider_adapter import (
    ComfyUIHttpClientPort,
    ComfyUIImagePrivateTransport,
)
from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    AuthoritativeWorkflowPageMappingDTO,
    WorkflowApplicationAuthorizationDTO,
)
from manga_director.production.next_generation_execution_authorization import (
    ExecutionAuthorizationRecordDTO,
    ExecutionAuthorizationValidationReport,
    ExecutionAuthorizationValidationService,
)
from manga_director.production.next_generation_generation_evidence import (
    EvidenceValueDTO,
    GenerationInputEvidenceDTO,
)
from manga_director.production.next_generation_generation_evidence_persistence import (
    LocalGenerationEvidenceStore,
)
from manga_director.production.next_generation_local_durable_asset_owner import (
    LocalDurableAssetOwner,
)
from manga_director.production.next_generation_normal_execution_attempt import (
    LocalNormalExecutionAttemptStore,
    NormalExecutionAttemptReservationDTO,
    NormalExecutionAttemptService,
    derive_execution_fingerprint,
)
from manga_director.production.next_generation_normal_execution_composition import (
    NormalExecutionCompositionFindingDTO,
    NormalExecutionCompositionInput,
    NormalExecutionCompositionReport,
    NormalExecutionCompositionService,
    _derived_reservation,
)
from manga_director.production.next_generation_pre_execution_readiness import (
    PreExecutionReadinessInputDTO,
    PreExecutionReadinessReport,
    PreExecutionReadinessService,
)
from manga_director.production.next_generation_provider_adapter_composition import (
    ProviderAdapterCompositionService,
)
from manga_director.production.next_generation_provider_capability_negotiation import (
    CapabilityNegotiationReport,
    GenerationCapabilityRequirementDTO,
    ProviderCapabilityDeclarationDTO,
    ProviderCapabilityNegotiationService,
    ProviderCapabilityStateDTO,
)
from manga_director.production.next_generation_provider_configuration import (
    AuthoritativeProviderConfigurationSnapshot,
    ProviderConfigurationNormalizationReport,
    ProviderConfigurationNormalizationService,
)
from manga_director.production.next_generation_provider_output_configuration import (
    ProviderOutputConfigurationBindingDTO,
    ProviderOutputConfigurationBindingReport,
)
from manga_director.production.next_generation_secure_execution_input_resolution import (
    AuthoritativeExecutionInputSnapshot,
    OpaqueReferenceAssetHandle,
)
from manga_director.production.next_generation_structured_generation_request import (
    GenerationProductionProfileDTO,
    StructuredGenerationRequestDTO,
    StructuredGenerationRequestValidationReport,
    StructuredGenerationRequestValidationService,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.local_file_durability import LocalFileDurabilityError
from manga_director.workflow.durable_execution import LocalFileDurablePageStore
from manga_director.workflow.engine import WorkflowEngine
from manga_director.workflow.localfile_external_generated_application import (
    _build_localfile_external_generation_composition_v1,
)
from manga_director.workflow.localfile_page_generation_mode_admission import (
    _admit_localfile_legacy_generation,
    _ModeGuardedAttemptStore,
    _ProviderApplicationAdmission,
    _replay_localfile_legacy_generated_application,
)
from manga_director.workflow.page_execution_fence import (
    PageExecutionFenceError,
    WindowsPageExecutionFence,
)

_PROVIDER_REFERENCE = "provider:comfyui"
_PROVIDER_ID = "comfyui"
_CHECKPOINT_ENVIRONMENT = "MANGA_DIRECTOR_COMFYUI_CHECKPOINT"
_PROFILE_ID = "profile:v7-04:prompt-only-png"
_PROFILE_VERSION = "v1"
_OUTPUT_SIZE = "1024x1024"
_OUTPUT_QUALITY = "medium"
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
_HUMAN_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_GENERIC_HUMAN_IDENTITIES = frozenset(
    {"anonymous", "default", "local-user", "system", "unknown", "user"}
)
_legacy_fence_factory = WindowsPageExecutionFence


@dataclass(frozen=True, slots=True)
class _ValidatedFacts:
    reservation: NormalExecutionAttemptReservationDTO
    structured: StructuredGenerationRequestValidationReport
    capability: CapabilityNegotiationReport
    readiness: PreExecutionReadinessReport
    execution: ExecutionAuthorizationValidationReport
    authorized_envelope: AuthorizedGenerationExecutionEnvelopeValidationReport
    configuration: ProviderConfigurationNormalizationReport
    output_configuration: ProviderOutputConfigurationBindingReport
    workflow_authorization: WorkflowApplicationAuthorizationDTO
    mapping: AuthoritativeWorkflowPageMappingDTO


class _PromptInputResolver:
    def __init__(self, input_reference: str, intent_reference: str, prompt: str) -> None:
        self._input_reference = input_reference
        self._snapshot = AuthoritativeExecutionInputSnapshot.from_prompt_material(
            input_reference=input_reference,
            generation_intent_reference=intent_reference,
            raw_prompt_material=prompt,
        )

    def resolve(self, input_reference: str) -> AuthoritativeExecutionInputSnapshot | None:
        return self._snapshot if input_reference == self._input_reference else None


class _NoReferenceAssetResolver:
    def resolve(self, reference_asset_id: str) -> OpaqueReferenceAssetHandle | None:
        del reference_asset_id
        return None


class _WorkflowContextLoader:
    def __init__(self, repository: LocalFileRepository) -> None:
        self._page_store = LocalFileDurablePageStore(repository)

    def load(self, project_id: str, page_id: str) -> object | None:
        fence = _legacy_fence_factory(project_id, page_id)
        fence.acquire()
        try:
            snapshot = self._page_store.load_revisioned(project_id)
            return self._page_store.context_from_snapshot(snapshot, page_id)
        finally:
            fence.release()


def execute_localfile_comfyui_real_image_generation(
    repository: LocalFileRepository,
    engine: WorkflowEngine,
    project_id: str,
    page_id: str,
    authorized_by: str,
    *,
    checkpoint_name: str | None = None,
    checkpoint_lookup: Callable[[str], str | None] | None = None,
    http_client: ComfyUIHttpClientPort | None = None,
    now: Callable[[], datetime] | None = None,
    token_factory: Callable[[], str] | None = None,
) -> NormalExecutionCompositionReport:
    """Run one prompt-only ComfyUI attempt through the existing durable chain."""

    if not isinstance(repository, LocalFileRepository):
        raise ValueError("real image generation requires the LocalFile repository")
    _validate_human_identity(authorized_by)
    observed_at = (now or (lambda: datetime.now(UTC)))()
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("real image generation requires a timezone-aware clock")
    token = (token_factory or (lambda: uuid.uuid4().hex))()
    if not _is_generated_token(token):
        raise ValueError("real image generation attempt identity is unavailable")

    request_id = f"request:v7-04:{token}"
    normalized_page_id = str(int(page_id))
    target_reference = _target_reference(project_id, normalized_page_id)
    intent_reference = f"intent:v7-04:{token}"
    input_reference = f"input:v7-04:{token}"
    execution_authorization_id = f"authorization:v7-04:{token}"
    workflow_authorization_id = f"workflow-authorization:v7-04:{authorized_by}:{token}"
    attempt_id = f"attempt:v7-04:{authorized_by}:{token}"
    try:
        context = _load_prompt_built_context(repository, project_id, normalized_page_id)
    except (LocalFileDurabilityError, PageExecutionFenceError):
        return _mode_blocked(attempt_id, project_id, normalized_page_id)
    mode_service, mode_result, mode_claim = _admit_localfile_legacy_generation(
        repository,
        project_id,
        normalized_page_id,
        attempt_id,
        authorized_by,
        _legacy_fence_factory(project_id, normalized_page_id),
    )
    if not mode_result.admitted or mode_claim is None or mode_service is None:
        return _mode_blocked(attempt_id, project_id, normalized_page_id)
    prompt: str | None = None
    checkpoint: str | None = None
    prompt, checkpoint = _prompt_and_checkpoint(
        context, checkpoint_name, checkpoint_lookup
    )

    root = repository._next_generation_normal_execution_owner_root()
    evidence_store = LocalGenerationEvidenceStore(root / "evidence")
    external_generation = _build_localfile_external_generation_composition_v1(
        repository,
        engine._state_machine,
        engine._event_bus,
        r25_composition=None,
    )
    provider_application = _ProviderApplicationAdmission(
        external_generation.external_application,
        evidence_store,
        root / "evidence",
        root / "assets",
        mode_service,
        mode_claim,
        _legacy_fence_factory,
    )
    if getattr(context, "state", None) == PageState.GENERATED:
        if _replay_localfile_legacy_generated_application(
            repository,
            attempt_id,
            authorized_by,
            observed_at,
            provider_application,
        ):
            return _replay_completed(attempt_id)
        return _mode_blocked(attempt_id, project_id, normalized_page_id)
    if prompt is None or checkpoint is None:
        return _mode_blocked(attempt_id, project_id, normalized_page_id)
    facts = _validated_facts(
        attempt_id=attempt_id,
        request_id=request_id,
        target_reference=target_reference,
        intent_reference=intent_reference,
        input_reference=input_reference,
        execution_authorization_id=execution_authorization_id,
        workflow_authorization_id=workflow_authorization_id,
        project_id=project_id,
        page_id=normalized_page_id,
        authorized_by=authorized_by,
        checkpoint_name=checkpoint,
        observed_at=observed_at,
    )
    transport = ComfyUIImagePrivateTransport(
        checkpoint,
        facts.output_configuration,
        http_client=http_client,
    )
    invocation = ProviderAdapterCompositionService().compose(
        facts.configuration,
        transport,
    )
    if invocation is None:
        raise ValueError("ComfyUI real image generation composition is unavailable")
    attempt_store = _ModeGuardedAttemptStore(
        LocalNormalExecutionAttemptStore(root / "attempts"),
        mode_service,
        mode_claim,
        _legacy_fence_factory,
    )
    asset_owner = LocalDurableAssetOwner(root / "assets", _issue_i02_commitment=False)
    asset_registration = ComfyUIOutputAssetRegistrationAdapter(
        ComfyUIAssetOwnerSinkBridge(asset_owner)
    )
    request = NormalExecutionCompositionInput(
        reservation=facts.reservation,
        structured_request_validation_report=facts.structured,
        capability_negotiation_report=facts.capability,
        pre_execution_readiness_report=facts.readiness,
        execution_authorization_validation_report=facts.execution,
        authorized_execution_envelope_validation_report=facts.authorized_envelope,
        workflow_application_authorization=facts.workflow_authorization,
        page_mapping=facts.mapping,
        workflow_context_loader=_WorkflowContextLoader(repository),
        generation_input_resolver=_PromptInputResolver(input_reference, intent_reference, prompt),
        reference_asset_resolver=_NoReferenceAssetResolver(),
        provider_invocation_port=invocation,
        asset_registration_port=asset_registration,
        evidence_store=evidence_store,
        external_application_coordinator=provider_application,
        observed_at=observed_at,
        provider_configuration_report=facts.configuration,
        provider_output_configuration_report=facts.output_configuration,
    )
    service = NormalExecutionCompositionService()
    if service._preflight(request):
        return service.execute(request, attempt_store)
    reserved = NormalExecutionAttemptService().reserve(
        _derived_reservation(request), attempt_store
    )
    if reserved.status == "blocked" or reserved.state != "RESERVED":
        return service.execute(request, attempt_store)
    # The immutable attempt now exists. This only network phase is read-only.
    transport.preflight()
    report = service.execute(request, attempt_store)
    return _as_recovery_required(report, project_id, normalized_page_id)


def _prompt_and_checkpoint(
    context: object,
    checkpoint_name: str | None,
    checkpoint_lookup: Callable[[str], str | None] | None,
) -> tuple[str | None, str | None]:
    if getattr(context, "state", None) != PageState.PROMPT_BUILT:
        return None, None
    return (
        _prompt_from_context(context),
        _require_checkpoint(checkpoint_name, checkpoint_lookup),
    )


def _validated_facts(  # noqa: C901 - mirrors the frozen V7-03 durable evidence chain.
    *,
    attempt_id: str,
    request_id: str,
    target_reference: str,
    intent_reference: str,
    input_reference: str,
    execution_authorization_id: str,
    workflow_authorization_id: str,
    project_id: str,
    page_id: str,
    authorized_by: str,
    checkpoint_name: str,
    observed_at: datetime,
) -> _ValidatedFacts:
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
    structured_request = StructuredGenerationRequestDTO(
        request_id=request_id,
        target_page_reference=target_reference,
        generation_intent_reference=intent_reference,
        input=GenerationInputEvidenceDTO(input_reference=input_reference),
        capability_requirements=requirements,
        provenance_reference=f"provenance:v7-04:{attempt_id.rsplit(':', 1)[-1]}",
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
    )
    structured = StructuredGenerationRequestValidationService().validate(
        structured_request, profile
    )
    capability = ProviderCapabilityNegotiationService().validate(
        requirements,
        ProviderCapabilityDeclarationDTO(
            provider_reference=_PROVIDER_REFERENCE,
            capability_states=(
                ProviderCapabilityStateDTO(capability_id="text_prompt", state="supported"),
                ProviderCapabilityStateDTO(capability_id="output_format", state="supported"),
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
                authorization_id=execution_authorization_id,
                authorizer_id=authorized_by,
                authorized_at=observed_at,
                request_id=request_id,
                provider_reference=_PROVIDER_REFERENCE,
            ),
        ),
    )
    envelope = AuthorizedGenerationExecutionEnvelopeDTO(
        attempt_id=attempt_id,
        request_id=request_id,
        provider_reference=_PROVIDER_REFERENCE,
        authorization_ids=(execution_authorization_id,),
        profile_id=profile.profile_id,
        profile_version=profile.profile_version,
        generation_intent_reference=intent_reference,
        input_reference=input_reference,
    )
    authorized_envelope = AuthorizedGenerationExecutionEnvelopeValidationService().validate(
        (envelope,), execution
    )
    configuration = ProviderConfigurationNormalizationService().normalize(
        attempt_id,
        AuthoritativeProviderConfigurationSnapshot(
            attempt_id=attempt_id,
            provider_reference=_PROVIDER_REFERENCE,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            provider_id=_known(_PROVIDER_ID),
            model_id=_known(checkpoint_name),
            model_version=_known("local-checkpoint"),
            workflow_id=_known("workflow:v7-04:fixed-core-png"),
            workflow_version=_known("v1"),
            requested_seed=_known("derived-from-attempt"),
        ),
        authorized_envelope,
    )
    output_configuration = ProviderOutputConfigurationBindingReport(
        provider_configuration_normalization_report=configuration,
        output_configuration=ProviderOutputConfigurationBindingDTO(
            attempt_id=attempt_id,
            provider_reference=_PROVIDER_REFERENCE,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            model_id=checkpoint_name,
            output_size=_OUTPUT_SIZE,
            output_quality=_OUTPUT_QUALITY,
        ),
        status="ready",
        ready=True,
    )
    reservation = NormalExecutionAttemptReservationDTO(
        attempt_id=attempt_id,
        request_id=request_id,
        project_id=project_id,
        page_id=page_id,
        target_page_reference=target_reference,
        provider_reference=_PROVIDER_REFERENCE,
        execution_fingerprint=derive_execution_fingerprint(
            {
                "attempt_id": attempt_id,
                "authorizer_id": authorized_by,
                "workflow_authorization_id": workflow_authorization_id,
            }
        ),
    )
    workflow_authorization = WorkflowApplicationAuthorizationDTO(
        authorization_id=workflow_authorization_id,
        authorizer_id=authorized_by,
        authorized_at=observed_at,
        attempt_id=attempt_id,
        provider_reference=_PROVIDER_REFERENCE,
        project_id=project_id,
        page_id=page_id,
        target_page_reference=target_reference,
        source_state="PromptBuilt",
        target_state="Generated",
    )
    mapping = AuthoritativeWorkflowPageMappingDTO(
        project_id=project_id,
        page_id=page_id,
        target_page_reference=target_reference,
    )
    return _ValidatedFacts(
        reservation=reservation,
        structured=structured,
        capability=capability,
        readiness=readiness,
        execution=execution,
        authorized_envelope=authorized_envelope,
        configuration=configuration,
        output_configuration=output_configuration,
        workflow_authorization=workflow_authorization,
        mapping=mapping,
    )


def _as_recovery_required(
    report: NormalExecutionCompositionReport,
    project_id: str,
    page_id: str,
) -> NormalExecutionCompositionReport:
    if report.completed or not report.provider_invocation_performed:
        return report
    finding = NormalExecutionCompositionFindingDTO(
        code="RECOVERY_REQUIRED",
        status="partial",
        message="manual recovery is required; automatic resubmission is prohibited",
        attempt_id=report.attempt_id,
        project_id=project_id,
        page_id=page_id,
    )
    return report.model_copy(update={"findings": (finding,), "status": "partial"})


def _load_prompt_built_context(
    repository: LocalFileRepository, project_id: str, page_id: str
) -> object:
    context = _WorkflowContextLoader(repository).load(project_id, str(int(page_id)))
    if context is None or getattr(context, "state", None) not in {
        PageState.PROMPT_BUILT,
        PageState.GENERATED,
    }:
        raise ValueError("real image generation requires one PromptBuilt page")
    return context


def _prompt_from_context(context: object) -> str:
    artifacts = getattr(context, "artifacts", None)
    prompt_artifact = artifacts.get(PageState.PROMPT_BUILT.value) if isinstance(artifacts, dict) else None
    prompt = prompt_artifact.get("prompt_markdown") if isinstance(prompt_artifact, dict) else None
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("real image generation requires a persisted prompt")
    return prompt.strip()


def _require_checkpoint(
    supplied: str | None,
    lookup: Callable[[str], str | None] | None,
) -> str:
    value = supplied
    if value is None:
        try:
            value = (lookup or os.getenv)(_CHECKPOINT_ENVIRONMENT)
        except Exception:
            value = None
    try:
        return validate_comfyui_checkpoint_name(value)
    except ValueError:
        raise ValueError(
            f"{_CHECKPOINT_ENVIRONMENT} must name one local .safetensors or .ckpt checkpoint"
        ) from None


def _validate_human_identity(value: str) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or any(character.isspace() for character in value)
        or value.startswith(("/", "\\"))
        or "://" in value
        or _WINDOWS_ABSOLUTE_PATH.match(value)
        or "@" in value
        or not _HUMAN_IDENTITY.fullmatch(value)
        or value.lower() in _GENERIC_HUMAN_IDENTITIES
        or any(part in value.lower() for part in _UNSAFE_IDENTITY_PARTS)
    ):
        raise ValueError("--authorized-by must identify one human authorizer")


def _is_generated_token(value: object) -> bool:
    return bool(
        isinstance(value, str)
        and len(value) == 32
        and all(character in "0123456789abcdef" for character in value)
    )


def _target_reference(project_id: str, page_id: str) -> str:
    digest = hashlib.sha256(f"{project_id}\0{page_id}".encode()).hexdigest()
    return f"target:v7-04:{digest[:32]}"


def _known(value: str) -> EvidenceValueDTO:
    return EvidenceValueDTO(availability="known", value=value)


def _mode_blocked(
    attempt_id: str, project_id: str, page_id: str
) -> NormalExecutionCompositionReport:
    return NormalExecutionCompositionReport(
        attempt_id=attempt_id,
        findings=(
            NormalExecutionCompositionFindingDTO(
                code="GENERATION_MODE_ADMISSION_BLOCKED",
                status="blocked",
                message="generation mode authority rejected the request",
                attempt_id=attempt_id,
                project_id=project_id,
                page_id=page_id,
            ),
        ),
        status="blocked",
        provider_invocation_performed=False,
        external_application_delegated=False,
        completed=False,
    )


def _replay_completed(attempt_id: str) -> NormalExecutionCompositionReport:
    return NormalExecutionCompositionReport(
        attempt_id=attempt_id,
        status="completed",
        provider_invocation_performed=False,
        external_application_delegated=True,
        completed=True,
    )
