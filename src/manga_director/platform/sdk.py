"""Typed v5 SDK foundation for read-only unified platform composition."""

from __future__ import annotations

from manga_director.platform.api_gateway import (
    UnifiedApiGatewayFoundation,
    UnifiedApiGatewayRequestDTO,
    UnifiedApiGatewayResponseDTO,
)
from manga_director.platform.automation import (
    AutomationEngineFoundation,
    AutomationEngineReport,
    AutomationRequestDTO,
)
from manga_director.platform.automation_intelligence import (
    AutomationDashboardDTO,
    AutomationIntelligenceService,
)
from manga_director.platform.automation_maturity import (
    AutomationPlatformMaturityReport,
    AutomationPlatformMaturityService,
)
from manga_director.platform.composition import (
    ModuleCompositionEngineFoundation,
    ModuleCompositionReport,
    ModuleCompositionRequestDTO,
)
from manga_director.platform.composition_maturity import (
    CompositionPlatformMaturityReport,
    CompositionPlatformMaturityService,
)
from manga_director.platform.context_intelligence import (
    UnifiedContextIntelligenceReport,
    UnifiedContextIntelligenceService,
)
from manga_director.platform.dashboard import (
    UnifiedPlatformDashboardDTO,
    UnifiedPlatformDashboardService,
)
from manga_director.platform.foundation import UnifiedContextReferenceDTO
from manga_director.platform.integration import (
    IntegrationGatewayFoundation,
    IntegrationGatewayReport,
    IntegrationRequestDTO,
)
from manga_director.platform.integration_intelligence import (
    IntegrationHealthDashboardDTO,
    IntegrationIntelligenceService,
)
from manga_director.platform.integration_maturity import (
    IntegrationPlatformMaturityReport,
    IntegrationPlatformMaturityService,
)
from manga_director.platform.maturity import (
    UnifiedPlatformMaturityReport,
    UnifiedPlatformMaturityService,
)
from manga_director.platform.orchestration import (
    UnifiedRuntimeOrchestrationReport,
    UnifiedRuntimeOrchestrationService,
)
from manga_director.platform.platform_lifecycle import (
    CreativePlatformLifecycleFoundation,
    PlatformLifecycleFoundationReport,
    PlatformLifecycleFoundationRequestDTO,
)
from manga_director.platform.platform_lifecycle_intelligence import (
    LifecycleIntelligenceService,
    MaintenanceDashboardDTO,
)
from manga_director.platform.platform_lifecycle_maturity import (
    PlatformLifecycleMaturityReport,
    PlatformLifecycleMaturityRequestDTO,
    PlatformLifecycleMaturityService,
)
from manga_director.platform.quality import (
    QualityEngineFoundation,
    QualityEngineReport,
    QualityEngineRequestDTO,
)
from manga_director.platform.quality_intelligence import (
    QualityIntelligenceService,
    QualityObservationDTO,
    ReleaseReadinessDashboardDTO,
)
from manga_director.platform.quality_maturity import (
    QualityFrameworkMaturityReport,
    QualityFrameworkMaturityService,
)
from manga_director.platform.runtime import (
    UnifiedRuntimeFoundationReport,
    UnifiedRuntimeFoundationService,
)
from manga_director.workflow.contracts import WorkflowContext


class UnifiedSDKFoundation:
    """An opt-in facade that delegates to the platform foundation unchanged."""

    def __init__(
        self,
        gateway: UnifiedApiGatewayFoundation | None = None,
        runtime: UnifiedRuntimeFoundationService | None = None,
        context_intelligence: UnifiedContextIntelligenceService | None = None,
        runtime_orchestration: UnifiedRuntimeOrchestrationService | None = None,
        dashboard: UnifiedPlatformDashboardService | None = None,
        maturity: UnifiedPlatformMaturityService | None = None,
        composition: ModuleCompositionEngineFoundation | None = None,
        composition_maturity: CompositionPlatformMaturityService | None = None,
        automation: AutomationEngineFoundation | None = None,
        automation_intelligence: AutomationIntelligenceService | None = None,
        automation_maturity: AutomationPlatformMaturityService | None = None,
        integration: IntegrationGatewayFoundation | None = None,
        integration_intelligence: IntegrationIntelligenceService | None = None,
        integration_maturity: IntegrationPlatformMaturityService | None = None,
        quality: QualityEngineFoundation | None = None,
        quality_intelligence: QualityIntelligenceService | None = None,
        quality_maturity: QualityFrameworkMaturityService | None = None,
        platform_lifecycle: CreativePlatformLifecycleFoundation | None = None,
        lifecycle_intelligence: LifecycleIntelligenceService | None = None,
        lifecycle_maturity: PlatformLifecycleMaturityService | None = None,
    ) -> None:
        self._gateway = gateway or UnifiedApiGatewayFoundation()
        self._runtime = runtime or UnifiedRuntimeFoundationService()
        self._context_intelligence = context_intelligence or UnifiedContextIntelligenceService()
        self._runtime_orchestration = runtime_orchestration or UnifiedRuntimeOrchestrationService(
            self._runtime
        )
        self._dashboard = dashboard or UnifiedPlatformDashboardService(
            context_intelligence=self._context_intelligence,
            runtime_orchestration=self._runtime_orchestration,
        )
        self._maturity = maturity or UnifiedPlatformMaturityService(dashboard=self._dashboard)
        self._composition = composition or ModuleCompositionEngineFoundation()
        self._composition_maturity = composition_maturity or CompositionPlatformMaturityService(
            engine=self._composition
        )
        self._automation = automation or AutomationEngineFoundation()
        self._automation_intelligence = (
            automation_intelligence or AutomationIntelligenceService(self._automation)
        )
        self._automation_maturity = automation_maturity or AutomationPlatformMaturityService(
            engine=self._automation,
            intelligence=self._automation_intelligence,
        )
        self._integration = integration or IntegrationGatewayFoundation()
        self._integration_intelligence = integration_intelligence or IntegrationIntelligenceService(
            self._integration
        )
        self._integration_maturity = integration_maturity or IntegrationPlatformMaturityService(
            self._integration
        )
        self._quality = quality or QualityEngineFoundation()
        self._quality_intelligence = quality_intelligence or QualityIntelligenceService(self._quality)
        self._quality_maturity = quality_maturity or QualityFrameworkMaturityService(
            self._quality, self._quality_intelligence
        )
        self._platform_lifecycle = platform_lifecycle or CreativePlatformLifecycleFoundation()
        self._lifecycle_intelligence = lifecycle_intelligence or LifecycleIntelligenceService(
            self._platform_lifecycle
        )
        self._lifecycle_maturity = lifecycle_maturity or PlatformLifecycleMaturityService(
            self._lifecycle_intelligence
        )

    def platform_preview(
        self,
        project_id: str,
        workflow_context: WorkflowContext,
        references: tuple[UnifiedContextReferenceDTO, ...] = (),
    ) -> UnifiedApiGatewayResponseDTO:
        return self._gateway.preview(
            UnifiedApiGatewayRequestDTO(project_id=project_id, references=references),
            workflow_context,
        )

    def runtime_preview(self) -> UnifiedRuntimeFoundationReport:
        return self._runtime.report()

    def context_intelligence(
        self,
        project_id: str,
        workflow_context: WorkflowContext,
        references: tuple[UnifiedContextReferenceDTO, ...] = (),
    ) -> UnifiedContextIntelligenceReport:
        return self._context_intelligence.report(
            self.platform_preview(project_id, workflow_context, references).report.context
        )

    def runtime_orchestration(self) -> UnifiedRuntimeOrchestrationReport:
        return self._runtime_orchestration.plan(self.runtime_preview())

    def dashboard(
        self,
        project_id: str,
        workflow_context: WorkflowContext,
        references: tuple[UnifiedContextReferenceDTO, ...] = (),
    ) -> UnifiedPlatformDashboardDTO:
        return self._dashboard.preview(project_id, workflow_context, references)

    def maturity(
        self,
        project_id: str,
        workflow_context: WorkflowContext,
        references: tuple[UnifiedContextReferenceDTO, ...] = (),
    ) -> UnifiedPlatformMaturityReport:
        return self._maturity.report(project_id, workflow_context, references)

    def composition_preview(self, request: ModuleCompositionRequestDTO) -> ModuleCompositionReport:
        """Returns declarative composition validation without runtime activation."""

        return self._composition.preview(request)

    def composition_maturity(
        self, request: ModuleCompositionRequestDTO
    ) -> CompositionPlatformMaturityReport:
        """Returns composition governance evidence without operating the platform."""

        return self._composition_maturity.report(request)

    def automation_preview(self, request: AutomationRequestDTO) -> AutomationEngineReport:
        """Returns an advisory, human-gated automation plan without executing it."""

        return self._automation.preview(request)

    def automation_dashboard(self, request: AutomationRequestDTO) -> AutomationDashboardDTO:
        """Returns read-only automation diagnostics without acting on a workflow."""

        return self._automation_intelligence.preview(request)

    def automation_maturity(
        self, request: AutomationRequestDTO
    ) -> AutomationPlatformMaturityReport:
        """Returns non-enforcing automation operating-quality evidence."""

        return self._automation_maturity.report(request)

    def integration_preview(self, request: IntegrationRequestDTO) -> IntegrationGatewayReport:
        """Returns a local, human-gated integration proposal without connecting."""

        return self._integration.preview(request)

    def integration_dashboard(self, request: IntegrationRequestDTO) -> IntegrationHealthDashboardDTO:
        """Returns local integration health diagnostics without a connection."""

        return self._integration_intelligence.preview(request)

    def integration_maturity(self, request: IntegrationRequestDTO) -> IntegrationPlatformMaturityReport:
        """Returns non-enforcing integration operating-quality evidence."""

        return self._integration_maturity.report(request)

    def quality_preview(self, request: QualityEngineRequestDTO) -> QualityEngineReport:
        """Returns a human-gated Quality Framework report without taking action."""

        return self._quality.preview(request)

    def quality_dashboard(
        self,
        request: QualityEngineRequestDTO,
        observations: tuple[QualityObservationDTO, ...] = (),
    ) -> ReleaseReadinessDashboardDTO:
        """Returns local quality analytics without monitoring or release operations."""

        return self._quality_intelligence.preview(request, observations)

    def quality_maturity(
        self,
        request: QualityEngineRequestDTO,
        observations: tuple[QualityObservationDTO, ...] = (),
    ) -> QualityFrameworkMaturityReport:
        """Returns non-enforcing quality governance and reliability evidence."""

        return self._quality_maturity.report(request, observations)

    def lifecycle_preview(
        self, request: PlatformLifecycleFoundationRequestDTO
    ) -> PlatformLifecycleFoundationReport:
        """Returns lifecycle evidence without upgrading, removing, or operating the platform."""

        return self._platform_lifecycle.preview(request)

    def lifecycle_dashboard(
        self, request: PlatformLifecycleFoundationRequestDTO
    ) -> MaintenanceDashboardDTO:
        """Returns advisory lifecycle analytics without upgrading or operating the platform."""

        return self._lifecycle_intelligence.preview(request)

    def lifecycle_maturity(
        self, request: PlatformLifecycleMaturityRequestDTO
    ) -> PlatformLifecycleMaturityReport:
        """Returns non-enforcing lifecycle operating-quality evidence."""

        return self._lifecycle_maturity.report(request)
