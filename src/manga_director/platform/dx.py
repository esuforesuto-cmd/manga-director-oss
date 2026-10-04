"""Developer-experience diagnostics for the read-only unified platform."""

from __future__ import annotations

from manga_director.platform.dashboard import UnifiedPlatformDashboardDTO
from manga_director.platform.operations import UnifiedReliabilityReport
from manga_director.production.director import DirectorModel


class UnifiedDXRecommendationDTO(DirectorModel):
    recommendation_id: str
    message: str
    requires_human_review: bool = True
    automatic_change_applied: bool = False


class UnifiedDeveloperExperienceReport(DirectorModel):
    dashboard: UnifiedPlatformDashboardDTO
    reliability: UnifiedReliabilityReport
    recommendations: tuple[UnifiedDXRecommendationDTO, ...]
    supported_entry_points: tuple[str, ...] = ("python", "cli", "fastapi", "mcp", "web-ui")
    configuration_changed: bool = False
    tooling_installed: bool = False
    planning_only: bool = True


class UnifiedDeveloperExperienceService:
    """Provides adoption guidance without changing developer configuration."""

    def report(
        self,
        dashboard: UnifiedPlatformDashboardDTO,
        reliability: UnifiedReliabilityReport,
    ) -> UnifiedDeveloperExperienceReport:
        recommendations = (
            UnifiedDXRecommendationDTO(
                recommendation_id="sdk-preview",
                message="Adopt the opt-in UnifiedSDKFoundation for read-only platform previews.",
            ),
            UnifiedDXRecommendationDTO(
                recommendation_id="context-provenance",
                message="Supply source-linked context references before composing a dashboard.",
            ),
        )
        return UnifiedDeveloperExperienceReport(
            dashboard=dashboard, reliability=reliability, recommendations=recommendations
        )
