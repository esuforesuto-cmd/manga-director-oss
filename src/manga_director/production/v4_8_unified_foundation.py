"""v4.8 Unified Platform foundation DTOs without runtime replacement.

The Creative Operating System foundation describes supplied scope, module and
service metadata, lifecycle references, and operational evidence for one
existing Page.  It does not register with the process runtime, alter existing
API routing, persist data, collect telemetry, dispatch work, or mutate a
workflow.  The domain StateMachine remains the only transition authority.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.workflow.contracts import WorkflowContext


class V48PlatformScopeDTO(DirectorModel):
    """A one-Page, caller-supplied scope reference for aggregate reports."""

    platform_id: str
    project_id: str
    page_reference: str
    page_count: Literal[1] = 1
    workflow_state: str
    state_machine_authoritative: bool = True
    scope_persisted: bool = False
    workflow_mutated: bool = False


class V48ServiceDescriptorDTO(DirectorModel):
    """Static metadata for an existing service; it is not a service handle."""

    service_id: str
    module_id: str
    capability_names: tuple[str, ...] = ()
    public_contract_preserved: bool = True
    runtime_registered: bool = False
    service_invoked: bool = False


class V48PlatformSummary(DirectorModel):
    service_count: int = Field(default=0, ge=0)
    provenance_required: bool = True
    redaction_required: bool = True
    aggregate_persisted: bool = False
    automatic_action_taken: bool = False


class UnifiedPlatformFoundationReport(DirectorModel):
    scope: V48PlatformScopeDTO
    services: tuple[V48ServiceDescriptorDTO, ...]
    summary: V48PlatformSummary
    planning_only: bool = True


class V48RuntimeModuleDTO(DirectorModel):
    """Declarative module boundary, not a dynamically activated module."""

    module_id: str
    owner_layer: str
    dependency_module_ids: tuple[str, ...] = ()
    core_dependency_direction_preserved: bool = True
    dynamically_loaded: bool = False
    runtime_activated: bool = False


class V48ModularRuntimeSummary(DirectorModel):
    module_count: int = Field(default=0, ge=0)
    existing_runtime_replaced: bool = False
    plugin_execution_enabled: bool = False
    automatic_action_taken: bool = False


class ModularRuntimeFoundationReport(DirectorModel):
    modules: tuple[V48RuntimeModuleDTO, ...]
    summary: V48ModularRuntimeSummary
    planning_only: bool = True


class V48ServiceRegistrySummary(DirectorModel):
    service_count: int = Field(default=0, ge=0)
    duplicate_service_count: int = Field(default=0, ge=0)
    external_discovery_performed: bool = False
    runtime_routing_changed: bool = False


class ServiceRegistryFoundationReport(DirectorModel):
    services: tuple[V48ServiceDescriptorDTO, ...]
    summary: V48ServiceRegistrySummary
    planning_only: bool = True


class UnifiedServiceRegistry:
    """An in-memory descriptor registry isolated from the application runtime.

    Callers explicitly supply service descriptors. Registering a descriptor
    records metadata only; it never imports, instantiates, invokes, routes, or
    exposes a service through existing delivery surfaces.
    """

    def __init__(self, descriptors: tuple[V48ServiceDescriptorDTO, ...] = ()) -> None:
        self._descriptors = {descriptor.service_id: descriptor for descriptor in descriptors}

    def register(self, descriptor: V48ServiceDescriptorDTO) -> None:
        if descriptor.service_id in self._descriptors:
            raise ValueError(f"duplicate service descriptor: {descriptor.service_id}")
        self._descriptors[descriptor.service_id] = descriptor

    def get(self, service_id: str) -> V48ServiceDescriptorDTO | None:
        return self._descriptors.get(service_id)

    def descriptors(self) -> tuple[V48ServiceDescriptorDTO, ...]:
        return tuple(self._descriptors[service_id] for service_id in sorted(self._descriptors))

    def report(self) -> ServiceRegistryFoundationReport:
        descriptors = self.descriptors()
        return ServiceRegistryFoundationReport(
            services=descriptors,
            summary=V48ServiceRegistrySummary(service_count=len(descriptors)),
        )


class V48LifecycleReferenceDTO(DirectorModel):
    lifecycle_id: str
    subject_type: str
    subject_id: str
    stage: str
    source_module: str
    page_count: Literal[1] = 1
    provenance_required: bool = True
    lifecycle_persisted: bool = False
    state_transitioned: bool = False


class V48LifecycleSummary(DirectorModel):
    reference_count: int = Field(default=1, ge=0)
    retention_policy_enforced: bool = False
    recovery_attempted: bool = False
    record_mutated: bool = False


class LifecycleManagerFoundationReport(DirectorModel):
    scope: V48PlatformScopeDTO
    references: tuple[V48LifecycleReferenceDTO, ...]
    summary: V48LifecycleSummary
    planning_only: bool = True


class LifecycleManager:
    """Builds descriptive lifecycle references without owning any lifecycle."""

    def reference(
        self,
        *,
        subject_type: str,
        subject_id: str,
        stage: str,
        source_module: str,
    ) -> V48LifecycleReferenceDTO:
        return V48LifecycleReferenceDTO(
            lifecycle_id=f"lifecycle:{source_module}:{subject_type}:{subject_id}",
            subject_type=subject_type,
            subject_id=subject_id,
            stage=stage,
            source_module=source_module,
        )


class V48OperationalSignalDTO(DirectorModel):
    signal_id: str
    domain: str
    status: Literal["unknown", "advisory"] = "unknown"
    evidence_supplied: bool = False
    freshness_assessed: bool = False
    telemetry_collected: bool = False
    operational_action_taken: bool = False


class V48OperationalIntelligenceSummary(DirectorModel):
    signal_count: int = Field(default=0, ge=0)
    presentation_dependency: bool = False
    report_persisted: bool = False
    monitoring_started: bool = False
    alert_sent: bool = False
    automatic_action_taken: bool = False


class OperationalIntelligenceFoundationReport(DirectorModel):
    scope: V48PlatformScopeDTO
    signals: tuple[V48OperationalSignalDTO, ...]
    summary: V48OperationalIntelligenceSummary
    planning_only: bool = True


class V48UnifiedPlatformFoundationService:
    """Compose non-executing v4.8 foundation reports over an existing Page."""

    def __init__(self, registry: UnifiedServiceRegistry | None = None) -> None:
        self._registry = registry or UnifiedServiceRegistry(_default_services())
        self._lifecycle_manager = LifecycleManager()

    def unified_platform(
        self, project_id: str, context: WorkflowContext
    ) -> UnifiedPlatformFoundationReport:
        scope = self._scope(project_id, context)
        services = self._registry.descriptors()
        return UnifiedPlatformFoundationReport(
            scope=scope,
            services=services,
            summary=V48PlatformSummary(service_count=len(services)),
        )

    def modular_runtime(self) -> ModularRuntimeFoundationReport:
        modules = _default_modules()
        return ModularRuntimeFoundationReport(
            modules=modules,
            summary=V48ModularRuntimeSummary(module_count=len(modules)),
        )

    def service_registry(self) -> ServiceRegistryFoundationReport:
        return self._registry.report()

    def lifecycle_manager(
        self, project_id: str, context: WorkflowContext
    ) -> LifecycleManagerFoundationReport:
        scope = self._scope(project_id, context)
        references = (
            self._lifecycle_manager.reference(
                subject_type="project",
                subject_id=project_id,
                stage="referenced",
                source_module="workspace",
            ),
            self._lifecycle_manager.reference(
                subject_type="page",
                subject_id=scope.page_reference,
                stage=scope.workflow_state,
                source_module="workflow",
            ),
        )
        return LifecycleManagerFoundationReport(
            scope=scope,
            references=references,
            summary=V48LifecycleSummary(reference_count=len(references)),
        )

    def operational_intelligence(
        self, project_id: str, context: WorkflowContext
    ) -> OperationalIntelligenceFoundationReport:
        scope = self._scope(project_id, context)
        signals = tuple(
            V48OperationalSignalDTO(signal_id=f"signal:{scope.platform_id}:{domain}", domain=domain)
            for domain in ("workspace", "agent-platform", "knowledge", "production", "enterprise", "decision")
        )
        return OperationalIntelligenceFoundationReport(
            scope=scope,
            signals=signals,
            summary=V48OperationalIntelligenceSummary(signal_count=len(signals)),
        )

    @staticmethod
    def _scope(project_id: str, context: WorkflowContext) -> V48PlatformScopeDTO:
        page_reference = _page_reference(context)
        return V48PlatformScopeDTO(
            platform_id=f"unified-platform:{project_id}:{page_reference}",
            project_id=project_id,
            page_reference=page_reference,
            workflow_state=context.state.value,
        )


def _default_services() -> tuple[V48ServiceDescriptorDTO, ...]:
    return (
        V48ServiceDescriptorDTO(
            service_id="workspace",
            module_id="workspace",
            capability_names=("scope", "collaboration"),
        ),
        V48ServiceDescriptorDTO(
            service_id="agent-platform",
            module_id="agent-platform",
            capability_names=("planning", "review"),
        ),
        V48ServiceDescriptorDTO(
            service_id="knowledge",
            module_id="knowledge",
            capability_names=("provenance", "graph"),
        ),
        V48ServiceDescriptorDTO(
            service_id="production",
            module_id="production",
            capability_names=("pipeline", "quality"),
        ),
        V48ServiceDescriptorDTO(
            service_id="enterprise",
            module_id="enterprise",
            capability_names=("governance", "reliability"),
        ),
        V48ServiceDescriptorDTO(
            service_id="decision",
            module_id="decision",
            capability_names=("recommendation", "approval-readiness"),
        ),
    )


def _default_modules() -> tuple[V48RuntimeModuleDTO, ...]:
    return (
        V48RuntimeModuleDTO(module_id="core", owner_layer="domain"),
        V48RuntimeModuleDTO(
            module_id="workspace", owner_layer="application", dependency_module_ids=("core",)
        ),
        V48RuntimeModuleDTO(
            module_id="agent-platform",
            owner_layer="application",
            dependency_module_ids=("core", "workspace"),
        ),
        V48RuntimeModuleDTO(
            module_id="knowledge", owner_layer="knowledge", dependency_module_ids=("core",)
        ),
        V48RuntimeModuleDTO(
            module_id="production",
            owner_layer="application",
            dependency_module_ids=("core", "knowledge"),
        ),
        V48RuntimeModuleDTO(
            module_id="enterprise",
            owner_layer="application",
            dependency_module_ids=("production",),
        ),
        V48RuntimeModuleDTO(
            module_id="decision",
            owner_layer="application",
            dependency_module_ids=("workspace", "knowledge", "production"),
        ),
    )


def _page_reference(context: WorkflowContext) -> str:
    page_id = context.page.get("id")
    return str(page_id) if page_id is not None else "page"
