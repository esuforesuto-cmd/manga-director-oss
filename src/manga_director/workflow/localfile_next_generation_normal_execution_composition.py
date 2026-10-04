"""Private LocalFile composition for a fake-only Next Generation normal attempt.

This module owns LocalFile durability construction only.  It delegates the
canonical generation chain and the external Generated application algorithm to
their existing owners, and it deliberately contains no public routing or real
provider composition.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from manga_director.domain.state_machine import StateMachine
from manga_director.events.bus import EventBus
from manga_director.production.next_generation_asset_registration import AssetRegistrationPort
from manga_director.production.next_generation_durable_evidence_workflow_binding import (
    AuthoritativeWorkflowPageMappingDTO,
    WorkflowApplicationAuthorizationDTO,
)
from manga_director.production.next_generation_execution_authorization import (
    ExecutionAuthorizationValidationReport,
)
from manga_director.production.next_generation_generation_evidence_persistence import (
    LocalGenerationEvidenceStore,
)
from manga_director.production.next_generation_local_durable_asset_owner import (
    LocalDurableAssetOwner,
    ProviderNeutralAssetOwner,
)
from manga_director.production.next_generation_normal_execution_attempt import (
    LocalNormalExecutionAttemptStore,
    NormalExecutionAttemptReservationDTO,
)
from manga_director.production.next_generation_normal_execution_composition import (
    NormalExecutionCompositionInput,
    NormalExecutionCompositionReport,
    NormalExecutionCompositionService,
)
from manga_director.production.next_generation_pre_execution_readiness import (
    PreExecutionReadinessReport,
)
from manga_director.production.next_generation_provider_capability_negotiation import (
    CapabilityNegotiationReport,
)
from manga_director.production.next_generation_provider_configuration import (
    ProviderConfigurationNormalizationReport,
)
from manga_director.production.next_generation_provider_invocation import (
    ProviderGenerationInvocationPort,
)
from manga_director.production.next_generation_provider_output_configuration import (
    ProviderOutputConfigurationBindingReport,
)
from manga_director.production.next_generation_secure_execution_input_resolution import (
    GenerationInputResolverPort,
    ReferenceAssetResolverPort,
)
from manga_director.production.next_generation_structured_generation_request import (
    StructuredGenerationRequestValidationReport,
)
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.workflow.durable_execution import LocalFileDurablePageStore
from manga_director.workflow.localfile_external_generated_application import (
    LocalFileExternalGenerationComposition,
    _build_localfile_external_generation_composition_v1,
)


@dataclass(frozen=True, slots=True)
class FakeNormalExecutionRuntimeEdges:
    """The only caller-injected, fake-only runtime edges for this composition."""

    fake_only: Literal[True]
    generation_input_resolver: GenerationInputResolverPort
    reference_asset_resolver: ReferenceAssetResolverPort
    provider_invocation_port: ProviderGenerationInvocationPort
    asset_registration_port_factory: Callable[[ProviderNeutralAssetOwner], AssetRegistrationPort]


@dataclass(frozen=True, slots=True)
class LocalFileNormalExecutionFacts:
    """Caller-supplied validated facts without LocalFile durable authorities."""

    reservation: NormalExecutionAttemptReservationDTO
    structured_request_validation_report: StructuredGenerationRequestValidationReport
    capability_negotiation_report: CapabilityNegotiationReport
    pre_execution_readiness_report: PreExecutionReadinessReport
    execution_authorization_validation_report: ExecutionAuthorizationValidationReport
    authorized_execution_envelope_validation_report: object
    workflow_application_authorization: WorkflowApplicationAuthorizationDTO
    page_mapping: AuthoritativeWorkflowPageMappingDTO
    observed_at: datetime
    provider_configuration_report: ProviderConfigurationNormalizationReport
    provider_output_configuration_report: ProviderOutputConfigurationBindingReport


class _LocalFileWorkflowContextLoader:
    """Load only the authoritative LocalFile page context for preflight."""

    def __init__(self, page_store: LocalFileDurablePageStore) -> None:
        self._page_store = page_store

    def load(self, project_id: str, page_id: str) -> object | None:
        snapshot = self._page_store.load_revisioned(project_id)
        return self._page_store.context_from_snapshot(snapshot, page_id)


@dataclass(frozen=True, slots=True)
class LocalFileNormalExecutionComposition:
    """Private assembled authorities for one or more fake-only normal attempts."""

    _service: NormalExecutionCompositionService
    _attempt_store: LocalNormalExecutionAttemptStore
    _evidence_store: LocalGenerationEvidenceStore
    _asset_owner: LocalDurableAssetOwner
    _asset_registration_port: AssetRegistrationPort
    _external_generation: LocalFileExternalGenerationComposition
    _context_loader: _LocalFileWorkflowContextLoader
    _runtime: FakeNormalExecutionRuntimeEdges

    def execute(self, facts: LocalFileNormalExecutionFacts) -> NormalExecutionCompositionReport:
        """Delegate exactly once through the pre-existing canonical chain."""

        request = NormalExecutionCompositionInput(
            reservation=facts.reservation,
            structured_request_validation_report=facts.structured_request_validation_report,
            capability_negotiation_report=facts.capability_negotiation_report,
            pre_execution_readiness_report=facts.pre_execution_readiness_report,
            execution_authorization_validation_report=(
                facts.execution_authorization_validation_report
            ),
            authorized_execution_envelope_validation_report=(
                facts.authorized_execution_envelope_validation_report
            ),
            workflow_application_authorization=facts.workflow_application_authorization,
            page_mapping=facts.page_mapping,
            workflow_context_loader=self._context_loader,
            generation_input_resolver=self._runtime.generation_input_resolver,
            reference_asset_resolver=self._runtime.reference_asset_resolver,
            provider_invocation_port=self._runtime.provider_invocation_port,
            asset_registration_port=self._asset_registration_port,
            evidence_store=self._evidence_store,
            external_application_coordinator=self._external_generation.external_application,
            observed_at=facts.observed_at,
            provider_configuration_report=facts.provider_configuration_report,
            provider_output_configuration_report=facts.provider_output_configuration_report,
        )
        return self._service.execute(request, self._attempt_store)


def build_localfile_fake_normal_execution_composition(
    repository: LocalFileRepository,
    state_machine: StateMachine,
    event_bus: EventBus,
    fake_runtime: FakeNormalExecutionRuntimeEdges,
) -> LocalFileNormalExecutionComposition:
    """Build private LocalFile owners without CLI, MCP, or real-provider routing."""

    if not isinstance(repository, LocalFileRepository):
        raise ValueError("trusted LocalFile repository is required")
    if fake_runtime.fake_only is not True:
        raise ValueError("fake-only runtime edges are required")

    root = repository._next_generation_normal_execution_owner_root()
    attempt_store = LocalNormalExecutionAttemptStore(root / "attempts")
    evidence_store = LocalGenerationEvidenceStore(root / "evidence")
    asset_owner = LocalDurableAssetOwner(root / "assets")
    try:
        asset_registration_port = fake_runtime.asset_registration_port_factory(asset_owner)
    except Exception as error:
        raise ValueError("fake asset-registration bridge is unavailable") from error
    if not callable(getattr(asset_registration_port, "register", None)):
        raise ValueError("fake asset-registration bridge is unavailable")

    page_store = LocalFileDurablePageStore(repository)
    external_generation = _build_localfile_external_generation_composition_v1(
        repository,
        state_machine,
        event_bus,
        r25_composition=None,
    )
    return LocalFileNormalExecutionComposition(
        _service=NormalExecutionCompositionService(),
        _attempt_store=attempt_store,
        _evidence_store=evidence_store,
        _asset_owner=asset_owner,
        _asset_registration_port=asset_registration_port,
        _external_generation=external_generation,
        _context_loader=_LocalFileWorkflowContextLoader(page_store),
        _runtime=fake_runtime,
    )
