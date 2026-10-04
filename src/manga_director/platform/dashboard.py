"""Read-only v5 unified platform dashboard composition."""

from __future__ import annotations

from manga_director.platform.api_surface import (
    UnifiedApiSurfaceReport,
    UnifiedApiSurfaceRequestDTO,
    UnifiedApiSurfaceService,
)
from manga_director.platform.context_intelligence import (
    UnifiedContextIntelligenceReport,
    UnifiedContextIntelligenceService,
)
from manga_director.platform.foundation import UnifiedContextReferenceDTO
from manga_director.platform.orchestration import (
    UnifiedRuntimeOrchestrationReport,
    UnifiedRuntimeOrchestrationService,
)
from manga_director.production.director import DirectorModel
from manga_director.workflow.contracts import WorkflowContext


class UnifiedPlatformDashboardDTO(DirectorModel):
    context_intelligence: UnifiedContextIntelligenceReport
    api_surface: UnifiedApiSurfaceReport
    runtime_orchestration: UnifiedRuntimeOrchestrationReport
    dashboard_persisted: bool = False
    presentation_dependency: bool = False
    automatic_action_taken: bool = False


class UnifiedPlatformDashboardService:
    """Combines supplied reports for presentation without owning a UI."""

    def __init__(
        self,
        api_surface: UnifiedApiSurfaceService | None = None,
        context_intelligence: UnifiedContextIntelligenceService | None = None,
        runtime_orchestration: UnifiedRuntimeOrchestrationService | None = None,
    ) -> None:
        self._api_surface = api_surface or UnifiedApiSurfaceService()
        self._context_intelligence = context_intelligence or UnifiedContextIntelligenceService()
        self._runtime_orchestration = runtime_orchestration or UnifiedRuntimeOrchestrationService()

    def preview(
        self,
        project_id: str,
        workflow_context: WorkflowContext,
        references: tuple[UnifiedContextReferenceDTO, ...] = (),
    ) -> UnifiedPlatformDashboardDTO:
        api_surface = self._api_surface.preview(
            UnifiedApiSurfaceRequestDTO(project_id=project_id, references=references),
            workflow_context,
        )
        return UnifiedPlatformDashboardDTO(
            context_intelligence=self._context_intelligence.report(api_surface.gateway.report.context),
            api_surface=api_surface,
            runtime_orchestration=self._runtime_orchestration.plan(),
        )

