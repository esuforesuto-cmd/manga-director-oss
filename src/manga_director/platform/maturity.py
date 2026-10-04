"""Composition service for v5 Platform Maturity reports without operations control."""

from __future__ import annotations

from manga_director.platform.dashboard import (
    UnifiedPlatformDashboardDTO,
    UnifiedPlatformDashboardService,
)
from manga_director.platform.dx import (
    UnifiedDeveloperExperienceReport,
    UnifiedDeveloperExperienceService,
)
from manga_director.platform.foundation import UnifiedContextReferenceDTO
from manga_director.platform.governance import (
    UnifiedPlatformGovernanceReport,
    UnifiedPlatformGovernanceService,
)
from manga_director.platform.lifecycle import UnifiedLifecycleReport, UnifiedLifecycleService
from manga_director.platform.operations import (
    UnifiedObservabilityReport,
    UnifiedObservabilityService,
    UnifiedReliabilityReport,
    UnifiedReliabilityService,
)
from manga_director.production.director import DirectorModel
from manga_director.workflow.contracts import WorkflowContext


class UnifiedPlatformMaturityReport(DirectorModel):
    dashboard: UnifiedPlatformDashboardDTO
    governance: UnifiedPlatformGovernanceReport
    observability: UnifiedObservabilityReport
    reliability: UnifiedReliabilityReport
    lifecycle: UnifiedLifecycleReport
    developer_experience: UnifiedDeveloperExperienceReport
    lts_candidate: bool = True
    automatic_action_taken: bool = False
    planning_only: bool = True


class UnifiedPlatformMaturityService:
    """Composes maturity evidence; it cannot monitor, govern, or operate a platform."""

    def __init__(
        self,
        dashboard: UnifiedPlatformDashboardService | None = None,
        governance: UnifiedPlatformGovernanceService | None = None,
        observability: UnifiedObservabilityService | None = None,
        reliability: UnifiedReliabilityService | None = None,
        lifecycle: UnifiedLifecycleService | None = None,
        developer_experience: UnifiedDeveloperExperienceService | None = None,
    ) -> None:
        self._dashboard = dashboard or UnifiedPlatformDashboardService()
        self._governance = governance or UnifiedPlatformGovernanceService()
        self._observability = observability or UnifiedObservabilityService()
        self._reliability = reliability or UnifiedReliabilityService()
        self._lifecycle = lifecycle or UnifiedLifecycleService()
        self._developer_experience = developer_experience or UnifiedDeveloperExperienceService()

    def report(
        self,
        project_id: str,
        workflow_context: WorkflowContext,
        references: tuple[UnifiedContextReferenceDTO, ...] = (),
    ) -> UnifiedPlatformMaturityReport:
        dashboard = self._dashboard.preview(project_id, workflow_context, references)
        observability = self._observability.report(dashboard)
        reliability = self._reliability.report(observability)
        return UnifiedPlatformMaturityReport(
            dashboard=dashboard,
            governance=self._governance.report(dashboard),
            observability=observability,
            reliability=reliability,
            lifecycle=self._lifecycle.report(dashboard.context_intelligence.context),
            developer_experience=self._developer_experience.report(dashboard, reliability),
        )

