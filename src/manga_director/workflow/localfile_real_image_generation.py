"""Private LocalFile composition for one explicitly authorized OpenAI image attempt."""

from __future__ import annotations

import hashlib
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib import import_module

from manga_director.domain.state_machine import PageState
from manga_director.production.future_real_delivery_i01 import StrictPngStructuralValidatorV1
from manga_director.production.next_generation_asset_registration import (
    AssetRegistrationRuntimeResult,
)
from manga_director.production.next_generation_authorized_execution_envelope import (
    AuthorizedGenerationExecutionEnvelopeDTO,
    AuthorizedGenerationExecutionEnvelopeValidationReport,
    AuthorizedGenerationExecutionEnvelopeValidationService,
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
    OwnerRegistrationMaterial,
)
from manga_director.production.next_generation_normal_execution_attempt import (
    LocalNormalExecutionAttemptStore,
    NormalExecutionAttemptReservationDTO,
    derive_execution_fingerprint,
)
from manga_director.production.next_generation_normal_execution_composition import (
    NormalExecutionCompositionInput,
    NormalExecutionCompositionReport,
    NormalExecutionCompositionService,
)
from manga_director.production.next_generation_openai_output_asset_registration import (
    OpenAIAssetOwnerSinkBridge,
    OpenAIOutputAssetRegistrationAdapter,
)
from manga_director.production.next_generation_openai_private_composition import (
    SecretLookup,
    compose_openai_private_invocation_adapter,
)
from manga_director.production.next_generation_openai_private_credentials import (
    ExactKeySecretManager,
    OpenAIPrivateCredentialResolver,
)
from manga_director.production.next_generation_openai_provider_adapter import (
    OpenAIImageClientFactoryPort,
)
from manga_director.production.next_generation_pre_execution_readiness import (
    PreExecutionReadinessInputDTO,
    PreExecutionReadinessReport,
    PreExecutionReadinessService,
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
    ProviderOutputConfigurationBindingService,
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
from manga_director.security import CredentialManager
from manga_director.workflow.durable_execution import LocalFileDurablePageStore
from manga_director.workflow.engine import WorkflowEngine
from manga_director.workflow.localfile_external_generated_application import (
    _build_localfile_external_generation_composition_v1,
)

_PROVIDER_REFERENCE = "provider:openai"
_PROVIDER_ID = "openai"
_MODEL_ID = "gpt-image-2-2026-04-21"
_SECRET_SELECTOR = "OPENAI_API_KEY"
_PROFILE_ID = "profile:v7-03:prompt-only-png"
_PROFILE_VERSION = "v1"
_OUTPUT_SIZE = "1536x1024"
_OUTPUT_QUALITY = "low"
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
        snapshot = self._page_store.load_revisioned(project_id)
        return self._page_store.context_from_snapshot(snapshot, page_id)


class _StrictPngAssetOwner:
    """Reject malformed PNG bytes before the durable owner receives them."""

    def __init__(self, owner: LocalDurableAssetOwner) -> None:
        self._owner = owner
        self._validator = StrictPngStructuralValidatorV1()

    def register(self, material: OwnerRegistrationMaterial) -> AssetRegistrationRuntimeResult:
        try:
            self._validator.validate(material.image_bytes)
        except (TypeError, ValueError):
            return AssetRegistrationRuntimeResult(
                attempt_id=material.attempt_id,
                provider_reference=material.provider_reference,
                outcome="failed",
            )
        return self._owner.register(material)


def execute_localfile_real_image_generation(
    repository: LocalFileRepository,
    engine: WorkflowEngine,
    project_id: str,
    page_id: str,
    authorized_by: str,
    *,
    secret_lookup: SecretLookup | None = None,
    client_factory: OpenAIImageClientFactoryPort | None = None,
    now: Callable[[], datetime] | None = None,
    token_factory: Callable[[], str] | None = None,
) -> NormalExecutionCompositionReport:
    """Run one prompt-only OpenAI attempt through the existing durable chain."""

    if not isinstance(repository, LocalFileRepository):
        raise ValueError("real image generation requires the LocalFile repository")
    _validate_human_identity(authorized_by)
    context = _load_prompt_built_context(repository, project_id, page_id)
    prompt = _prompt_from_context(context)
    credential = _require_openai_runtime(secret_lookup, client_factory)

    observed_at = (now or (lambda: datetime.now(UTC)))()
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("real image generation requires a timezone-aware clock")
    token = (token_factory or (lambda: uuid.uuid4().hex))()
    if not _is_generated_token(token):
        raise ValueError("real image generation attempt identity is unavailable")

    request_id = f"request:v7-03:{token}"
    normalized_page_id = str(int(page_id))
    target_reference = _target_reference(project_id, normalized_page_id)
    intent_reference = f"intent:v7-03:{token}"
    input_reference = f"input:v7-03:{token}"
    execution_authorization_id = f"authorization:v7-03:{token}"
    workflow_authorization_id = (
        f"workflow-authorization:v7-03:{authorized_by}:{token}"
    )
    attempt_id = f"attempt:v7-03:{authorized_by}:{token}"
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
        observed_at=observed_at,
    )
    invocation = compose_openai_private_invocation_adapter(
        _SECRET_SELECTOR,
        facts.configuration,
        facts.output_configuration,
        secret_lookup=lambda name: credential if name == _SECRET_SELECTOR else None,
        client_factory=client_factory,
    )
    if invocation is None:
        raise ValueError("OpenAI real image generation composition is unavailable")

    root = repository._next_generation_normal_execution_owner_root()
    attempt_store = LocalNormalExecutionAttemptStore(root / "attempts")
    evidence_store = LocalGenerationEvidenceStore(root / "evidence")
    asset_owner = LocalDurableAssetOwner(root / "assets", _issue_i02_commitment=False)
    asset_registration = OpenAIOutputAssetRegistrationAdapter(
        OpenAIAssetOwnerSinkBridge(_StrictPngAssetOwner(asset_owner))
    )
    external_generation = _build_localfile_external_generation_composition_v1(
        repository,
        engine._state_machine,
        engine._event_bus,
        r25_composition=None,
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
        generation_input_resolver=_PromptInputResolver(
            input_reference, intent_reference, prompt
        ),
        reference_asset_resolver=_NoReferenceAssetResolver(),
        provider_invocation_port=invocation,
        asset_registration_port=asset_registration,
        evidence_store=evidence_store,
        external_application_coordinator=external_generation.external_application,
        observed_at=observed_at,
        provider_configuration_report=facts.configuration,
        provider_output_configuration_report=facts.output_configuration,
    )
    return NormalExecutionCompositionService().execute(request, attempt_store)


def _validated_facts(
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
        provenance_reference=f"provenance:v7-03:{attempt_id.rsplit(':', 1)[-1]}",
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
            model_id=_known(_MODEL_ID),
            model_version=_known("model-version:2026-04-21"),
            workflow_id=_known("workflow:v7-03:real-image"),
            workflow_version=_known("v1"),
            requested_seed=_known("not-requested"),
        ),
        authorized_envelope,
    )
    output_configuration = ProviderOutputConfigurationBindingService().validate(
        ProviderOutputConfigurationBindingDTO(
            attempt_id=attempt_id,
            provider_reference=_PROVIDER_REFERENCE,
            profile_id=profile.profile_id,
            profile_version=profile.profile_version,
            model_id=_MODEL_ID,
            output_size=_OUTPUT_SIZE,
            output_quality=_OUTPUT_QUALITY,
        ),
        configuration,
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


def _load_prompt_built_context(
    repository: LocalFileRepository, project_id: str, page_id: str
) -> object:
    context = _WorkflowContextLoader(repository).load(project_id, str(int(page_id)))
    if context is None or getattr(context, "state", None) != PageState.PROMPT_BUILT:
        raise ValueError("real image generation requires one PromptBuilt page")
    return context


def _prompt_from_context(context: object) -> str:
    artifacts = getattr(context, "artifacts", None)
    prompt_artifact = artifacts.get(PageState.PROMPT_BUILT.value) if isinstance(artifacts, dict) else None
    prompt = prompt_artifact.get("prompt_markdown") if isinstance(prompt_artifact, dict) else None
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("real image generation requires a persisted prompt")
    return prompt


def _require_openai_runtime(
    secret_lookup: SecretLookup | None,
    client_factory: OpenAIImageClientFactoryPort | None,
) -> str:
    if client_factory is None:
        try:
            import_module("openai")
        except ImportError:
            raise ValueError(
                'OpenAI support is unavailable; install the existing ".[openai]" extra'
            ) from None
    resolver = OpenAIPrivateCredentialResolver(
        CredentialManager(ExactKeySecretManager(_SECRET_SELECTOR, secret_lookup)),
        _SECRET_SELECTOR,
    )
    try:
        credential = resolver.resolve()
    except Exception:
        raise ValueError("OPENAI_API_KEY is unavailable") from None
    if not credential.strip():
        raise ValueError("OPENAI_API_KEY is unavailable")
    return credential


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
    return f"target:v7-03:{digest[:32]}"


def _known(value: str) -> EvidenceValueDTO:
    return EvidenceValueDTO(availability="known", value=value)
