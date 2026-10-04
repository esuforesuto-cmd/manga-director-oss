"""v5.1 composition governance, observability, lifecycle, and reliability.

These services analyze a supplied composition preview only.  They never enforce
policy, collect telemetry, activate modules, persist lifecycle state, recover
components, or alter the workflow StateMachine.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.platform.composition import (
    ModuleCompositionEngineFoundation,
    ModuleCompositionReport,
    ModuleCompositionRequestDTO,
)
from manga_director.production.director import DirectorModel


class CompositionPolicyDTO(DirectorModel):
    policy_id: str = "composition-policy"
    state_machine_authoritative: bool = True
    one_page_scope_required: bool = True
    persisted_storyboard_required: bool = True
    completed_quality_review_required: bool = True
    human_review_required: bool = True
    policy_enforced: bool = False


class CompositionComplianceDTO(DirectorModel):
    policy_id: str
    profile_legacy_fallback: bool
    metadata_valid: bool
    public_contract_preserved: bool
    compliance_confirmed: bool = False
    enforcement_action_taken: bool = False


class CompositionGovernanceSummary(DirectorModel):
    human_review_required: bool = True
    policy_count: int = Field(default=1, ge=0)
    automatic_action_taken: bool = False


class CompositionGovernanceReport(DirectorModel):
    composition: ModuleCompositionReport
    policy: CompositionPolicyDTO
    compliance: CompositionComplianceDTO
    summary: CompositionGovernanceSummary
    planning_only: bool = True


class CompositionGovernanceService:
    """Produces non-enforcing governance evidence for a composition preview."""

    def report(self, composition: ModuleCompositionReport) -> CompositionGovernanceReport:
        policy = CompositionPolicyDTO()
        return CompositionGovernanceReport(
            composition=composition,
            policy=policy,
            compliance=CompositionComplianceDTO(
                policy_id=policy.policy_id,
                profile_legacy_fallback=composition.profile.profile.legacy_only_fallback,
                metadata_valid=composition.summary.valid,
                public_contract_preserved=all(
                    item.public_contract_preserved for item in composition.registry.capabilities
                ),
            ),
            summary=CompositionGovernanceSummary(),
        )


class CapabilityPolicyDTO(DirectorModel):
    policy_id: str = "capability-policy"
    compatibility_range_required: bool = True
    owner_module_required: bool = True
    public_contract_preserved_required: bool = True
    dynamic_loading_prohibited: bool = True
    policy_enforced: bool = False


class CapabilityComplianceDTO(DirectorModel):
    capability_id: str
    owner_module_declared: bool
    compatibility_declared: bool
    public_contract_preserved: bool
    dynamically_loaded: bool = False
    compliance_confirmed: bool = False


class CapabilityGovernanceReport(DirectorModel):
    composition: ModuleCompositionReport
    policy: CapabilityPolicyDTO
    capabilities: tuple[CapabilityComplianceDTO, ...]
    capability_count: int = Field(default=0, ge=0)
    external_audit_performed: bool = False
    planning_only: bool = True


class CapabilityGovernanceService:
    """Audits descriptor declarations without loading or auditing a module."""

    def report(self, composition: ModuleCompositionReport) -> CapabilityGovernanceReport:
        capabilities = tuple(
            CapabilityComplianceDTO(
                capability_id=item.capability_id,
                owner_module_declared=bool(item.owner_module),
                compatibility_declared=bool(item.compatibility),
                public_contract_preserved=item.public_contract_preserved,
                dynamically_loaded=item.dynamically_loaded,
            )
            for item in composition.registry.capabilities
        )
        return CapabilityGovernanceReport(
            composition=composition,
            policy=CapabilityPolicyDTO(),
            capabilities=capabilities,
            capability_count=len(capabilities),
        )


class CompositionObservationDTO(DirectorModel):
    observation_id: str
    component: str
    status: Literal["available", "invalid"]
    evidence_supplied: bool = True
    telemetry_collected: bool = False
    alert_sent: bool = False


class CompositionObservabilityReport(DirectorModel):
    composition: ModuleCompositionReport
    observations: tuple[CompositionObservationDTO, ...]
    observation_count: int = Field(default=0, ge=0)
    monitoring_started: bool = False
    report_persisted: bool = False
    planning_only: bool = True


class CompositionObservabilityService:
    """Creates local observations from a preview without operational monitoring."""

    def report(self, composition: ModuleCompositionReport) -> CompositionObservabilityReport:
        status: Literal["available", "invalid"] = (
            "available" if composition.summary.valid else "invalid"
        )
        observations = (
            CompositionObservationDTO(
                observation_id="capability-registry", component="registry", status=status
            ),
            CompositionObservationDTO(
                observation_id="feature-packs", component="feature-packs", status=status
            ),
            CompositionObservationDTO(
                observation_id="platform-profile", component="profile", status=status
            ),
            CompositionObservationDTO(
                observation_id="solution-templates", component="templates", status=status
            ),
            CompositionObservationDTO(
                observation_id="composition-engine", component="engine", status=status
            ),
        )
        return CompositionObservabilityReport(
            composition=composition,
            observations=observations,
            observation_count=len(observations),
        )


class ModuleLifecycleDTO(DirectorModel):
    module_id: str
    owner_module: str
    stage: Literal["declared"] = "declared"
    public_contract_preserved: bool
    lifecycle_transitioned: bool = False
    lifecycle_persisted: bool = False


class ModuleLifecycleReport(DirectorModel):
    composition: ModuleCompositionReport
    modules: tuple[ModuleLifecycleDTO, ...]
    module_count: int = Field(default=0, ge=0)
    ownership_transferred: bool = False
    retention_enforced: bool = False
    recovery_attempted: bool = False
    planning_only: bool = True


class ModuleLifecycleManagementService:
    """Describes module ownership lifecycle without changing lifecycle state."""

    def report(self, composition: ModuleCompositionReport) -> ModuleLifecycleReport:
        modules = tuple(
            ModuleLifecycleDTO(
                module_id=item.capability_id,
                owner_module=item.owner_module,
                public_contract_preserved=item.public_contract_preserved,
            )
            for item in composition.registry.capabilities
        )
        return ModuleLifecycleReport(
            composition=composition, modules=modules, module_count=len(modules)
        )


class CompositionReliabilityComponentDTO(DirectorModel):
    component_id: str
    status: Literal["metadata_valid", "metadata_invalid"]
    compatibility_required: bool = True
    health_check_performed: bool = False
    recovery_attempted: bool = False


class CompositionReliabilityReport(DirectorModel):
    observability: CompositionObservabilityReport
    components: tuple[CompositionReliabilityComponentDTO, ...]
    component_count: int = Field(default=0, ge=0)
    runtime_reconfigured: bool = False
    automatic_recovery_taken: bool = False
    planning_only: bool = True


class CompositionReliabilityService:
    """Reports metadata confidence and never diagnoses or repairs a runtime."""

    def report(self, observability: CompositionObservabilityReport) -> CompositionReliabilityReport:
        status: Literal["metadata_valid", "metadata_invalid"] = (
            "metadata_valid" if observability.composition.summary.valid else "metadata_invalid"
        )
        components = tuple(
            CompositionReliabilityComponentDTO(component_id=observation.component, status=status)
            for observation in observability.observations
        )
        return CompositionReliabilityReport(
            observability=observability,
            components=components,
            component_count=len(components),
        )


class CompositionPlatformMaturityReport(DirectorModel):
    composition: ModuleCompositionReport
    governance: CompositionGovernanceReport
    capability_governance: CapabilityGovernanceReport
    observability: CompositionObservabilityReport
    lifecycle: ModuleLifecycleReport
    reliability: CompositionReliabilityReport
    lts_compatible: bool = True
    automatic_action_taken: bool = False
    planning_only: bool = True


class CompositionPlatformMaturityService:
    """Composes v5.1 operating-quality evidence from supplied metadata."""

    def __init__(
        self,
        engine: ModuleCompositionEngineFoundation | None = None,
        governance: CompositionGovernanceService | None = None,
        capability_governance: CapabilityGovernanceService | None = None,
        observability: CompositionObservabilityService | None = None,
        lifecycle: ModuleLifecycleManagementService | None = None,
        reliability: CompositionReliabilityService | None = None,
    ) -> None:
        self._engine = engine or ModuleCompositionEngineFoundation()
        self._governance = governance or CompositionGovernanceService()
        self._capability_governance = capability_governance or CapabilityGovernanceService()
        self._observability = observability or CompositionObservabilityService()
        self._lifecycle = lifecycle or ModuleLifecycleManagementService()
        self._reliability = reliability or CompositionReliabilityService()

    def report(self, request: ModuleCompositionRequestDTO) -> CompositionPlatformMaturityReport:
        composition = self._engine.preview(request)
        observability = self._observability.report(composition)
        return CompositionPlatformMaturityReport(
            composition=composition,
            governance=self._governance.report(composition),
            capability_governance=self._capability_governance.report(composition),
            observability=observability,
            lifecycle=self._lifecycle.report(composition),
            reliability=self._reliability.report(observability),
        )
