"""Read-only v6.0 Platform Kernel and enterprise-operation projections.

This Application-layer module composes the existing v6.0 intelligence reports
and the unified-context foundation.  All entries are caller supplied.  The
service never starts a runtime, loads an extension, creates a marketplace
listing, enforces a policy, persists governance evidence, emits telemetry, or
changes a Page workflow.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.production.v6_0_foundation import (
    CollaborationAssignmentDTO,
    KnowledgeCoreReferenceDTO,
    ProjectHubReferenceDTO,
    ServiceRegistryEntryDTO,
    V60CreativeProductionPlatformFoundationService,
    WorkspaceHubReferenceDTO,
)
from manga_director.production.v6_0_intelligence import (
    ContextEngineReport,
    CreativeProductionPlatformIntelligenceReport,
    KnowledgeGraphEdgeDTO,
    V60AutomationRuleDTO,
    V60CreativeProductionPlatformIntelligenceService,
)
from manga_director.workflow.contracts import WorkflowContext


class V60UnifiedContextReferenceDTO(DirectorModel):
    domain: Literal["workspace", "knowledge", "agent", "production"]
    context_id: str
    source_module: str
    source_reference: str
    source_loaded: Literal[False] = False
    source_mutated: Literal[False] = False


class V60UnifiedCreativeContextDTO(DirectorModel):
    context_id: str
    project_id: str
    page_reference: str
    workflow_state: str
    references: tuple[V60UnifiedContextReferenceDTO, ...] = ()
    page_count: Literal[1] = 1
    context_persisted: Literal[False] = False
    workflow_mutated: Literal[False] = False


class V60UnifiedContextSourceReport(DirectorModel):
    context: V60UnifiedCreativeContextDTO
    domain_count: int = Field(default=0, ge=0)
    source_of_truth_transferred: Literal[False] = False
    planning_only: Literal[True] = True


class PlatformKernelDTO(DirectorModel):
    kernel_id: str
    project_id: str
    page_reference: str
    capability_ids: tuple[str, ...] = ()
    context_reference_count: int = Field(default=0, ge=0)
    kernel_started: Literal[False] = False
    runtime_changed: Literal[False] = False


class PlatformKernelReport(DirectorModel):
    kernel: PlatformKernelDTO
    intelligence: CreativeProductionPlatformIntelligenceReport
    v5_compatibility_preserved: Literal[True] = True
    automatic_action_taken: Literal[False] = False
    planning_only: Literal[True] = True


class UnifiedContextManagerReport(DirectorModel):
    context: V60UnifiedCreativeContextDTO
    source_report: V60UnifiedContextSourceReport
    context_engine: ContextEngineReport
    context_mutated: Literal[False] = False
    prompt_generated: Literal[False] = False
    planning_only: Literal[True] = True


class ExtensionFrameworkDTO(DirectorModel):
    extension_id: str
    name: str
    extension_type: Literal["sdk", "automation", "knowledge", "collaboration", "analytics"]
    compatibility: Literal["v5_additive", "v6_foundation"]
    capability_ids: tuple[str, ...] = ()
    extension_registered: Literal[False] = False
    extension_loaded: Literal[False] = False
    extension_executed: Literal[False] = False


class ExtensionFrameworkReport(DirectorModel):
    extensions: tuple[ExtensionFrameworkDTO, ...] = ()
    compatible: bool
    duplicate_extension_ids: tuple[str, ...] = ()
    extension_runtime_changed: Literal[False] = False
    planning_only: Literal[True] = True


class SDKCapabilityDTO(DirectorModel):
    capability_id: str
    surface: Literal["python", "cli", "fastapi", "mcp", "web_ui"]
    source_reference: str
    compatibility: Literal["v5_additive", "v6_foundation"]
    sdk_generated: Literal[False] = False


class SDKFoundationReport(DirectorModel):
    capabilities: tuple[SDKCapabilityDTO, ...] = ()
    surface_count: int = Field(default=0, ge=0)
    compatible: bool
    sdk_published: Literal[False] = False
    public_api_changed: Literal[False] = False
    planning_only: Literal[True] = True


class MarketplaceListingDTO(DirectorModel):
    listing_id: str
    name: str
    listing_type: Literal["extension", "workflow_template", "solution_template"]
    compatibility: Literal["v5_additive", "v6_foundation"]
    review_required: Literal[True] = True
    listing_published: Literal[False] = False
    package_installed: Literal[False] = False


class MarketplaceFrameworkReport(DirectorModel):
    listings: tuple[MarketplaceListingDTO, ...] = ()
    valid: bool
    duplicate_listing_ids: tuple[str, ...] = ()
    marketplace_contacted: Literal[False] = False
    marketplace_mutated: Literal[False] = False
    planning_only: Literal[True] = True


class PlatformPolicyDTO(DirectorModel):
    policy_id: str
    scope: Literal["kernel", "context", "extension", "marketplace", "governance", "observability"]
    requires_human_approval: Literal[True] = True
    policy_enforced: Literal[False] = False


class PolicyEngineReport(DirectorModel):
    policies: tuple[PlatformPolicyDTO, ...] = ()
    valid: bool
    duplicate_policy_ids: tuple[str, ...] = ()
    policy_persisted: Literal[False] = False
    enforcement_performed: Literal[False] = False
    planning_only: Literal[True] = True


class GovernanceControlDTO(DirectorModel):
    control_id: str
    policy_id: str
    area: Literal["sdk", "extension", "marketplace", "workflow", "analytics"]
    review_required: Literal[True] = True
    control_applied: Literal[False] = False


class GovernanceFrameworkReport(DirectorModel):
    controls: tuple[GovernanceControlDTO, ...] = ()
    valid: bool
    missing_policy_ids: tuple[str, ...] = ()
    governance_persisted: Literal[False] = False
    compliance_decision_automated: Literal[False] = False
    planning_only: Literal[True] = True


class ObservabilityMetricDTO(DirectorModel):
    metric_id: str
    value: int = Field(ge=0)
    source: Literal["computed", "supplied"]
    telemetry_emitted: Literal[False] = False


class ObservabilityPlatformReport(DirectorModel):
    metrics: tuple[ObservabilityMetricDTO, ...] = ()
    metric_count: int = Field(default=0, ge=0)
    dashboard_ready: bool
    telemetry_persisted: Literal[False] = False
    alert_dispatched: Literal[False] = False
    planning_only: Literal[True] = True


class CreativeProductionPlatformCoreCompletionReport(DirectorModel):
    kernel: PlatformKernelReport
    unified_context: UnifiedContextManagerReport
    extensions: ExtensionFrameworkReport
    sdk: SDKFoundationReport
    marketplace: MarketplaceFrameworkReport
    policy: PolicyEngineReport
    governance: GovernanceFrameworkReport
    observability: ObservabilityPlatformReport
    v5_compatibility_preserved: Literal[True] = True
    enterprise_operation_ready: bool
    automatic_action_taken: Literal[False] = False
    planning_only: Literal[True] = True


class V60CreativeProductionPlatformCoreService:
    """Compose v6.0 platform-core diagnostics without ownership transfer."""

    def __init__(self) -> None:
        self._intelligence = V60CreativeProductionPlatformIntelligenceService()
        self._foundation = V60CreativeProductionPlatformFoundationService()

    def unified_context_manager(
        self,
        project_id: str,
        context: WorkflowContext,
        references: tuple[V60UnifiedContextReferenceDTO, ...] = (),
    ) -> UnifiedContextManagerReport:
        context_engine = self._intelligence.context_engine(project_id, context)
        _require_unique((reference.domain for reference in references), "context domain")
        production = self._foundation.production_core(project_id, context).production
        unified_context = V60UnifiedCreativeContextDTO(
            context_id=f"unified-context:{project_id}:{production.page_reference}",
            project_id=project_id,
            page_reference=production.page_reference,
            workflow_state=production.current_state.value,
            references=references,
        )
        source_report = V60UnifiedContextSourceReport(
            context=unified_context,
            domain_count=len(references),
        )
        return UnifiedContextManagerReport(
            context=unified_context,
            source_report=source_report,
            context_engine=context_engine,
        )

    def extension_framework(
        self, extensions: tuple[ExtensionFrameworkDTO, ...] = ()
    ) -> ExtensionFrameworkReport:
        ids = tuple(extension.extension_id for extension in extensions)
        duplicates = _duplicates(ids)
        ordered = tuple(sorted(extensions, key=lambda item: item.extension_id))
        return ExtensionFrameworkReport(
            extensions=ordered,
            compatible=not duplicates
            and all(
                extension.compatibility in {"v5_additive", "v6_foundation"}
                and not extension.extension_loaded
                and not extension.extension_executed
                for extension in ordered
            ),
            duplicate_extension_ids=duplicates,
        )

    def sdk_foundation(self, capabilities: tuple[SDKCapabilityDTO, ...] = ()) -> SDKFoundationReport:
        _require_unique((capability.capability_id for capability in capabilities), "capability_id")
        ordered = tuple(sorted(capabilities, key=lambda item: item.capability_id))
        return SDKFoundationReport(
            capabilities=ordered,
            surface_count=len({capability.surface for capability in ordered}),
            compatible=all(capability.compatibility in {"v5_additive", "v6_foundation"} for capability in ordered),
        )

    def marketplace_framework(
        self, listings: tuple[MarketplaceListingDTO, ...] = ()
    ) -> MarketplaceFrameworkReport:
        ids = tuple(listing.listing_id for listing in listings)
        duplicates = _duplicates(ids)
        ordered = tuple(sorted(listings, key=lambda item: item.listing_id))
        return MarketplaceFrameworkReport(
            listings=ordered,
            valid=not duplicates
            and all(
                listing.review_required
                and not listing.listing_published
                and not listing.package_installed
                for listing in ordered
            ),
            duplicate_listing_ids=duplicates,
        )

    def policy_engine(self, policies: tuple[PlatformPolicyDTO, ...] = ()) -> PolicyEngineReport:
        ids = tuple(policy.policy_id for policy in policies)
        duplicates = _duplicates(ids)
        ordered = tuple(sorted(policies, key=lambda item: item.policy_id))
        return PolicyEngineReport(
            policies=ordered,
            valid=not duplicates
            and all(policy.requires_human_approval and not policy.policy_enforced for policy in ordered),
            duplicate_policy_ids=duplicates,
        )

    def governance_framework(
        self,
        controls: tuple[GovernanceControlDTO, ...] = (),
        policies: tuple[PlatformPolicyDTO, ...] = (),
    ) -> GovernanceFrameworkReport:
        _require_unique((control.control_id for control in controls), "control_id")
        policy_ids = {policy.policy_id for policy in policies}
        ordered = tuple(sorted(controls, key=lambda item: item.control_id))
        missing = tuple(sorted({control.policy_id for control in ordered if control.policy_id not in policy_ids}))
        return GovernanceFrameworkReport(
            controls=ordered,
            valid=not missing
            and all(control.review_required and not control.control_applied for control in ordered),
            missing_policy_ids=missing,
        )

    def observability_platform(
        self,
        kernel: PlatformKernelReport,
        extensions: ExtensionFrameworkReport,
        marketplace: MarketplaceFrameworkReport,
        metrics: tuple[ObservabilityMetricDTO, ...] = (),
    ) -> ObservabilityPlatformReport:
        _require_unique((metric.metric_id for metric in metrics), "metric_id")
        computed = (
            ObservabilityMetricDTO(
                metric_id="knowledge_nodes",
                value=kernel.intelligence.analytics.analytics.knowledge_node_count,
                source="computed",
            ),
            ObservabilityMetricDTO(
                metric_id="extensions_observed",
                value=len(extensions.extensions),
                source="computed",
            ),
            ObservabilityMetricDTO(
                metric_id="marketplace_listings_observed",
                value=len(marketplace.listings),
                source="computed",
            ),
        )
        all_metrics = (*computed, *metrics)
        _require_unique((metric.metric_id for metric in all_metrics), "metric_id")
        ordered = tuple(sorted(all_metrics, key=lambda item: item.metric_id))
        return ObservabilityPlatformReport(
            metrics=ordered,
            metric_count=len(ordered),
            dashboard_ready=kernel.intelligence.analytics.analytics.quality_review_completed,
        )

    def platform_kernel(
        self, intelligence: CreativeProductionPlatformIntelligenceReport
    ) -> PlatformKernelReport:
        production = intelligence.foundation.production.production
        capability_ids = tuple(
            sorted(
                {
                    "knowledge-graph",
                    "context-engine",
                    "workflow-orchestrator",
                    "automation-hub",
                    "collaboration-workspace",
                    "production-analytics",
                    "service-discovery",
                }
            )
        )
        return PlatformKernelReport(
            kernel=PlatformKernelDTO(
                kernel_id=f"platform-kernel:{production.project_id}:{production.page_reference}",
                project_id=production.project_id,
                page_reference=production.page_reference,
                capability_ids=capability_ids,
                context_reference_count=len(intelligence.context.fragments),
            ),
            intelligence=intelligence,
        )

    def platform_core(
        self,
        project_id: str,
        context: WorkflowContext,
        *,
        projects: tuple[ProjectHubReferenceDTO, ...] = (),
        workspaces: tuple[WorkspaceHubReferenceDTO, ...] = (),
        knowledge: tuple[KnowledgeCoreReferenceDTO, ...] = (),
        knowledge_edges: tuple[KnowledgeGraphEdgeDTO, ...] = (),
        assignments: tuple[CollaborationAssignmentDTO, ...] = (),
        services: tuple[ServiceRegistryEntryDTO, ...] = (),
        automation_rules: tuple[V60AutomationRuleDTO, ...] = (),
        context_references: tuple[V60UnifiedContextReferenceDTO, ...] = (),
        extensions: tuple[ExtensionFrameworkDTO, ...] = (),
        sdk_capabilities: tuple[SDKCapabilityDTO, ...] = (),
        marketplace_listings: tuple[MarketplaceListingDTO, ...] = (),
        policies: tuple[PlatformPolicyDTO, ...] = (),
        governance_controls: tuple[GovernanceControlDTO, ...] = (),
        metrics: tuple[ObservabilityMetricDTO, ...] = (),
    ) -> CreativeProductionPlatformCoreCompletionReport:
        intelligence = self._intelligence.intelligence(
            project_id,
            context,
            projects=projects,
            workspaces=workspaces,
            knowledge=knowledge,
            knowledge_edges=knowledge_edges,
            assignments=assignments,
            services=services,
            automation_rules=automation_rules,
        )
        kernel = self.platform_kernel(intelligence)
        unified_context = self.unified_context_manager(project_id, context, context_references)
        extension_report = self.extension_framework(extensions)
        sdk = self.sdk_foundation(sdk_capabilities)
        marketplace = self.marketplace_framework(marketplace_listings)
        policy = self.policy_engine(policies)
        governance = self.governance_framework(governance_controls, policies)
        observability = self.observability_platform(kernel, extension_report, marketplace, metrics)
        return CreativeProductionPlatformCoreCompletionReport(
            kernel=kernel,
            unified_context=unified_context,
            extensions=extension_report,
            sdk=sdk,
            marketplace=marketplace,
            policy=policy,
            governance=governance,
            observability=observability,
            enterprise_operation_ready=(
                extension_report.compatible
                and sdk.compatible
                and marketplace.valid
                and policy.valid
                and governance.valid
                and observability.dashboard_ready
            ),
        )


def _duplicates(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted({value for value in values if values.count(value) > 1}))


def _require_unique(values: Iterable[str], field_name: str) -> None:
    items = tuple(values)
    if len(items) != len(set(items)):
        raise ValueError(f"{field_name} values must be unique")
