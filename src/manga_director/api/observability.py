"""Transport-neutral observability application service and optional FastAPI routes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from manga_director._version import __version__
from manga_director.observability import RuntimeDiagnosticReport, RuntimeHealthReport
from manga_director.repositories.integrity import RepositoryCheckReport


class ObservabilityApplication:
    """Expose DTOs only; it has no dependency on FastAPI or workflow internals."""

    def __init__(
        self,
        *,
        health: Callable[[], RuntimeHealthReport],
        diagnostics: Callable[[], RuntimeDiagnosticReport],
        repository_check: Callable[[], RepositoryCheckReport],
        planning: Callable[[], Any] | None = None,
        provider_selection: Callable[[], Any] | None = None,
        analytics: Callable[[], Any] | None = None,
        enterprise: Callable[[], Any] | None = None,
        executive: Callable[[], Any] | None = None,
        assurance: Callable[[], Any] | None = None,
        provider_governance: Callable[[], Any] | None = None,
        dashboard: Callable[[], Any] | None = None,
        director: Callable[[], Any] | None = None,
        knowledge: Callable[[], Any] | None = None,
        orchestration: Callable[[], Any] | None = None,
        director_analysis: Callable[[], Any] | None = None,
        optimization_dashboard: Callable[[], Any] | None = None,
        director_reliability: Callable[[], Any] | None = None,
        knowledge_governance: Callable[[], Any] | None = None,
        enterprise_ai_readiness: Callable[[], Any] | None = None,
        ai_workflow_diagnostics: Callable[[], Any] | None = None,
        director_dashboard: Callable[[], Any] | None = None,
        director_platform: Callable[[], Any] | None = None,
        creative_planning: Callable[[], Any] | None = None,
        knowledge_foundation: Callable[[], Any] | None = None,
        workflow_intelligence: Callable[[], Any] | None = None,
        planning_foundation_summary: Callable[[], Any] | None = None,
        multi_agent: Callable[[], Any] | None = None,
        creative_knowledge: Callable[[], Any] | None = None,
        director_intelligence: Callable[[], Any] | None = None,
        review_pipeline: Callable[[], Any] | None = None,
        knowledge_relationship: Callable[[], Any] | None = None,
        director_reliability_v3: Callable[[], Any] | None = None,
        creative_governance: Callable[[], Any] | None = None,
        knowledge_integrity: Callable[[], Any] | None = None,
        production_readiness: Callable[[], Any] | None = None,
        release_readiness: Callable[[], Any] | None = None,
        collaboration_foundation: Callable[[], Any] | None = None,
        knowledge_evolution: Callable[[], Any] | None = None,
        operations_foundation: Callable[[], Any] | None = None,
        developer_productivity: Callable[[], Any] | None = None,
        project_metrics: Callable[[], Any] | None = None,
        creative_review: Callable[[], Any] | None = None,
        knowledge_analytics: Callable[[], Any] | None = None,
        operations_intelligence: Callable[[], Any] | None = None,
        developer_experience: Callable[[], Any] | None = None,
        workflow_efficiency: Callable[[], Any] | None = None,
        creative_governance_v31: Callable[[], Any] | None = None,
        knowledge_reliability: Callable[[], Any] | None = None,
        operational_readiness_v31: Callable[[], Any] | None = None,
        release_quality: Callable[[], Any] | None = None,
        compatibility_validation: Callable[[], Any] | None = None,
        creative_studio_v32: Callable[[], Any] | None = None,
        asset_intelligence_v32: Callable[[], Any] | None = None,
        workflow_profiles_v32: Callable[[], Any] | None = None,
        production_analytics_v32: Callable[[], Any] | None = None,
        workspace_dashboard_v32: Callable[[], Any] | None = None,
        creative_workspace_v32: Callable[[], Any] | None = None,
        asset_analytics_v32: Callable[[], Any] | None = None,
        workflow_intelligence_v32: Callable[[], Any] | None = None,
        production_insights_v32: Callable[[], Any] | None = None,
        pipeline_analysis_v32: Callable[[], Any] | None = None,
        creative_reliability_v32: Callable[[], Any] | None = None,
        asset_governance_v32: Callable[[], Any] | None = None,
        operational_intelligence_v32: Callable[[], Any] | None = None,
        release_readiness_v32: Callable[[], Any] | None = None,
        compatibility_validation_v32: Callable[[], Any] | None = None,
        production_pipeline_v33: Callable[[], Any] | None = None,
        quality_intelligence_v33: Callable[[], Any] | None = None,
        asset_lifecycle_v33: Callable[[], Any] | None = None,
        project_intelligence_v33: Callable[[], Any] | None = None,
        production_intelligence_v33: Callable[[], Any] | None = None,
        quality_analytics_v33: Callable[[], Any] | None = None,
        asset_intelligence_v33: Callable[[], Any] | None = None,
        project_operations_v33: Callable[[], Any] | None = None,
        production_governance_v33: Callable[[], Any] | None = None,
        quality_governance_v33: Callable[[], Any] | None = None,
        asset_governance_v33: Callable[[], Any] | None = None,
        project_governance_v33: Callable[[], Any] | None = None,
        knowledge_platform_v34: Callable[[], Any] | None = None,
        production_operations_v34: Callable[[], Any] | None = None,
        organization_intelligence_v34: Callable[[], Any] | None = None,
        release_intelligence_v34: Callable[[], Any] | None = None,
        knowledge_intelligence_v34: Callable[[], Any] | None = None,
        production_optimization_v34: Callable[[], Any] | None = None,
        organization_analytics_v34: Callable[[], Any] | None = None,
        release_analytics_v34: Callable[[], Any] | None = None,
        knowledge_governance_v34: Callable[[], Any] | None = None,
        production_governance_v34: Callable[[], Any] | None = None,
        organization_governance_v34: Callable[[], Any] | None = None,
        release_governance_v34: Callable[[], Any] | None = None,
        knowledge_graph_v35: Callable[[], Any] | None = None,
        creative_intelligence_v35: Callable[[], Any] | None = None,
        production_intelligence_v35: Callable[[], Any] | None = None,
        platform_analytics_v35: Callable[[], Any] | None = None,
        knowledge_insights_v35: Callable[[], Any] | None = None,
        creative_analytics_v35: Callable[[], Any] | None = None,
        production_analytics_v35: Callable[[], Any] | None = None,
        executive_analytics_v35: Callable[[], Any] | None = None,
        knowledge_governance_v35: Callable[[], Any] | None = None,
        creative_governance_v35: Callable[[], Any] | None = None,
        production_governance_v35: Callable[[], Any] | None = None,
        platform_governance_v35: Callable[[], Any] | None = None,
    ) -> None:
        self._health = health
        self._diagnostics = diagnostics
        self._repository_check = repository_check
        self._planning = planning
        self._provider_selection = provider_selection
        self._analytics = analytics
        self._enterprise = enterprise
        self._executive = executive
        self._assurance = assurance
        self._provider_governance = provider_governance
        self._dashboard = dashboard
        self._director = director
        self._knowledge = knowledge
        self._orchestration = orchestration
        self._director_analysis = director_analysis
        self._optimization_dashboard = optimization_dashboard
        self._director_reliability = director_reliability
        self._knowledge_governance = knowledge_governance
        self._enterprise_ai_readiness = enterprise_ai_readiness
        self._ai_workflow_diagnostics = ai_workflow_diagnostics
        self._director_dashboard = director_dashboard
        self._director_platform = director_platform
        self._creative_planning = creative_planning
        self._knowledge_foundation = knowledge_foundation
        self._workflow_intelligence = workflow_intelligence
        self._planning_foundation_summary = planning_foundation_summary
        self._multi_agent = multi_agent
        self._creative_knowledge = creative_knowledge
        self._director_intelligence = director_intelligence
        self._review_pipeline = review_pipeline
        self._knowledge_relationship = knowledge_relationship
        self._director_reliability_v3 = director_reliability_v3
        self._creative_governance = creative_governance
        self._knowledge_integrity = knowledge_integrity
        self._production_readiness = production_readiness
        self._release_readiness = release_readiness
        self._collaboration_foundation = collaboration_foundation
        self._knowledge_evolution = knowledge_evolution
        self._operations_foundation = operations_foundation
        self._developer_productivity = developer_productivity
        self._project_metrics = project_metrics
        self._creative_review = creative_review
        self._knowledge_analytics = knowledge_analytics
        self._operations_intelligence = operations_intelligence
        self._developer_experience = developer_experience
        self._workflow_efficiency = workflow_efficiency
        self._creative_governance_v31 = creative_governance_v31
        self._knowledge_reliability = knowledge_reliability
        self._operational_readiness_v31 = operational_readiness_v31
        self._release_quality = release_quality
        self._compatibility_validation = compatibility_validation
        self._creative_studio_v32 = creative_studio_v32
        self._asset_intelligence_v32 = asset_intelligence_v32
        self._workflow_profiles_v32 = workflow_profiles_v32
        self._production_analytics_v32 = production_analytics_v32
        self._workspace_dashboard_v32 = workspace_dashboard_v32
        self._creative_workspace_v32 = creative_workspace_v32
        self._asset_analytics_v32 = asset_analytics_v32
        self._workflow_intelligence_v32 = workflow_intelligence_v32
        self._production_insights_v32 = production_insights_v32
        self._pipeline_analysis_v32 = pipeline_analysis_v32
        self._creative_reliability_v32 = creative_reliability_v32
        self._asset_governance_v32 = asset_governance_v32
        self._operational_intelligence_v32 = operational_intelligence_v32
        self._release_readiness_v32 = release_readiness_v32
        self._compatibility_validation_v32 = compatibility_validation_v32
        self._production_pipeline_v33 = production_pipeline_v33
        self._quality_intelligence_v33 = quality_intelligence_v33
        self._asset_lifecycle_v33 = asset_lifecycle_v33
        self._project_intelligence_v33 = project_intelligence_v33
        self._production_intelligence_v33 = production_intelligence_v33
        self._quality_analytics_v33 = quality_analytics_v33
        self._asset_intelligence_v33 = asset_intelligence_v33
        self._project_operations_v33 = project_operations_v33
        self._production_governance_v33 = production_governance_v33
        self._quality_governance_v33 = quality_governance_v33
        self._asset_governance_v33 = asset_governance_v33
        self._project_governance_v33 = project_governance_v33
        self._knowledge_platform_v34 = knowledge_platform_v34
        self._production_operations_v34 = production_operations_v34
        self._organization_intelligence_v34 = organization_intelligence_v34
        self._release_intelligence_v34 = release_intelligence_v34
        self._knowledge_intelligence_v34 = knowledge_intelligence_v34
        self._production_optimization_v34 = production_optimization_v34
        self._organization_analytics_v34 = organization_analytics_v34
        self._release_analytics_v34 = release_analytics_v34
        self._knowledge_governance_v34 = knowledge_governance_v34
        self._production_governance_v34 = production_governance_v34
        self._organization_governance_v34 = organization_governance_v34
        self._release_governance_v34 = release_governance_v34
        self._knowledge_graph_v35 = knowledge_graph_v35
        self._creative_intelligence_v35 = creative_intelligence_v35
        self._production_intelligence_v35 = production_intelligence_v35
        self._platform_analytics_v35 = platform_analytics_v35
        self._knowledge_insights_v35 = knowledge_insights_v35
        self._creative_analytics_v35 = creative_analytics_v35
        self._production_analytics_v35 = production_analytics_v35
        self._executive_analytics_v35 = executive_analytics_v35
        self._knowledge_governance_v35 = knowledge_governance_v35
        self._creative_governance_v35 = creative_governance_v35
        self._production_governance_v35 = production_governance_v35
        self._platform_governance_v35 = platform_governance_v35

    def health_summary(self) -> dict[str, Any]:
        return self._health().model_dump(mode="json")

    def provider_health(self) -> dict[str, Any]:
        return self._health().provider.model_dump(mode="json")

    def backend_health(self) -> dict[str, Any]:
        return self._health().backend.model_dump(mode="json")

    def diagnostics_report(self) -> dict[str, Any]:
        return self._diagnostics().model_dump(mode="json")

    def repository_integrity(self) -> dict[str, Any]:
        return self._repository_check().model_dump(mode="json")

    def planning_preview(self) -> dict[str, Any]:
        """Return an optional, read-only workflow planning DTO."""

        return _dto_or_unavailable(self._planning, "workflow planning not configured")

    def provider_preview(self) -> dict[str, Any]:
        """Return an optional, metadata-only provider selection DTO."""

        return _dto_or_unavailable(self._provider_selection, "provider planning not configured")

    def workflow_analytics(self) -> dict[str, Any]:
        """Return an optional, read-only workflow analysis DTO."""

        return _dto_or_unavailable(self._analytics, "workflow analytics not configured")

    def enterprise_diagnostics(self) -> dict[str, Any]:
        """Return an optional presentation-independent enterprise diagnostics DTO."""

        return _dto_or_unavailable(self._enterprise, "enterprise diagnostics not configured")

    def executive_analytics(self) -> dict[str, Any]:
        """Return an optional executive analytics DTO with no workflow control."""

        return _dto_or_unavailable(self._executive, "executive analytics not configured")

    def workflow_assurance(self) -> dict[str, Any]:
        """Return an optional, read-only AI workflow reliability DTO."""

        return _dto_or_unavailable(self._assurance, "workflow assurance not configured")

    def provider_governance(self) -> dict[str, Any]:
        """Return optional local metadata-only Provider governance evidence."""

        return _dto_or_unavailable(self._provider_governance, "provider governance not configured")

    def executive_dashboard(self) -> dict[str, Any]:
        """Return an optional dashboard DTO that cannot trigger a release or workflow step."""

        return _dto_or_unavailable(self._dashboard, "executive dashboard not configured")

    def director_preview(self) -> dict[str, Any]:
        return _dto_or_unavailable(self._director, "AI Director not configured")

    def knowledge_preview(self) -> dict[str, Any]:
        return _dto_or_unavailable(self._knowledge, "Knowledge service not configured")

    def orchestration_preview(self) -> dict[str, Any]:
        return _dto_or_unavailable(self._orchestration, "Workflow Orchestration not configured")

    def director_analysis_preview(self) -> dict[str, Any]:
        return _dto_or_unavailable(self._director_analysis, "Director analysis not configured")

    def optimization_dashboard_preview(self) -> dict[str, Any]:
        return _dto_or_unavailable(
            self._optimization_dashboard, "Optimization dashboard not configured"
        )

    def director_reliability_preview(self) -> dict[str, Any]:
        return _dto_or_unavailable(
            self._director_reliability, "AI Director reliability not configured"
        )

    def knowledge_governance_preview(self) -> dict[str, Any]:
        return _dto_or_unavailable(
            self._knowledge_governance, "Knowledge governance not configured"
        )

    def enterprise_ai_readiness_preview(self) -> dict[str, Any]:
        return _dto_or_unavailable(
            self._enterprise_ai_readiness, "enterprise AI readiness not configured"
        )

    def ai_workflow_diagnostics_preview(self) -> dict[str, Any]:
        return _dto_or_unavailable(
            self._ai_workflow_diagnostics, "AI workflow diagnostics not configured"
        )

    def director_dashboard_preview(self) -> dict[str, Any]:
        return _dto_or_unavailable(self._director_dashboard, "Director dashboard not configured")

    def director_platform_preview(self) -> dict[str, Any]:
        """Return a v3 Director session DTO without workflow control."""

        return _dto_or_unavailable(self._director_platform, "v3 Director Platform not configured")

    def creative_planning_preview(self) -> dict[str, Any]:
        """Return a v3 Creative Planning DTO without image generation."""

        return _dto_or_unavailable(self._creative_planning, "v3 Creative Planning not configured")

    def knowledge_foundation_preview(self) -> dict[str, Any]:
        """Return a repository-derived v3 Knowledge Foundation DTO."""

        return _dto_or_unavailable(
            self._knowledge_foundation, "v3 Knowledge Foundation not configured"
        )

    def workflow_intelligence_preview(self) -> dict[str, Any]:
        """Return a v3 diagnostic Workflow Intelligence DTO."""

        return _dto_or_unavailable(
            self._workflow_intelligence, "v3 Workflow Intelligence not configured"
        )

    def planning_foundation_summary_preview(self) -> dict[str, Any]:
        """Return a compact v3 planning summary without execution capability."""

        return _dto_or_unavailable(
            self._planning_foundation_summary, "v3 planning summary not configured"
        )

    def multi_agent_preview(self) -> dict[str, Any]:
        """Return a v3 collaboration plan with no Agent dispatch capability."""

        return _dto_or_unavailable(self._multi_agent, "v3 Multi-Agent Foundation not configured")

    def creative_knowledge_preview(self) -> dict[str, Any]:
        """Return a v3 repository-derived Creative Knowledge DTO."""

        return _dto_or_unavailable(self._creative_knowledge, "v3 Creative Knowledge not configured")

    def director_intelligence_preview(self) -> dict[str, Any]:
        """Return v3 creative decision and recommendation evidence only."""

        return _dto_or_unavailable(
            self._director_intelligence, "v3 Director Intelligence not configured"
        )

    def review_pipeline_preview(self) -> dict[str, Any]:
        """Return v3 diagnostic review evidence without approval authority."""

        return _dto_or_unavailable(self._review_pipeline, "v3 Review Pipeline not configured")

    def knowledge_relationship_preview(self) -> dict[str, Any]:
        """Return the v3 read-only Creative Knowledge relationship graph."""

        return _dto_or_unavailable(
            self._knowledge_relationship, "v3 Knowledge Relationship not configured"
        )

    def director_reliability_v3_preview(self) -> dict[str, Any]:
        """Return v3 Director validation evidence without workflow execution."""

        return _dto_or_unavailable(
            self._director_reliability_v3, "v3 Director Reliability not configured"
        )

    def creative_governance_preview(self) -> dict[str, Any]:
        """Return v3 Creative governance evidence without artifact mutation."""

        return _dto_or_unavailable(
            self._creative_governance, "v3 Creative Governance not configured"
        )

    def knowledge_integrity_preview(self) -> dict[str, Any]:
        """Return a v3 read-only Knowledge integrity DTO."""

        return _dto_or_unavailable(
            self._knowledge_integrity, "v3 Knowledge Integrity not configured"
        )

    def production_readiness_preview(self) -> dict[str, Any]:
        """Return v3 deployment-readiness evidence without deployment."""

        return _dto_or_unavailable(
            self._production_readiness, "v3 Production Readiness not configured"
        )

    def release_readiness_preview(self) -> dict[str, Any]:
        """Return the v3 release-readiness dashboard without release authority."""

        return _dto_or_unavailable(self._release_readiness, "v3 Release Readiness not configured")

    def collaboration_foundation_preview(self) -> dict[str, Any]:
        """Return v3.1 workspace evidence without Agent execution or approval."""

        return _dto_or_unavailable(
            self._collaboration_foundation, "v3.1 Collaboration Foundation not configured"
        )

    def knowledge_evolution_preview(self) -> dict[str, Any]:
        """Return v3.1 repository-derived Knowledge history without writes."""

        return _dto_or_unavailable(
            self._knowledge_evolution, "v3.1 Knowledge Evolution not configured"
        )

    def operations_foundation_preview(self) -> dict[str, Any]:
        """Return v3.1 operational metrics without automation."""

        return _dto_or_unavailable(
            self._operations_foundation, "v3.1 Operations Foundation not configured"
        )

    def developer_productivity_preview(self) -> dict[str, Any]:
        """Return v3.1 template descriptors without generating files."""

        return _dto_or_unavailable(
            self._developer_productivity, "v3.1 Developer Productivity not configured"
        )

    def project_metrics_preview(self) -> dict[str, Any]:
        """Return v3.1 aggregate Project metrics without workflow execution."""

        return _dto_or_unavailable(self._project_metrics, "v3.1 Project Metrics not configured")

    def creative_review_preview(self) -> dict[str, Any]:
        """Return v3.1 review evidence without executing review or approval."""

        return _dto_or_unavailable(self._creative_review, "v3.1 Creative Review not configured")

    def knowledge_analytics_preview(self) -> dict[str, Any]:
        """Return v3.1 redacted Knowledge analytics without writes."""

        return _dto_or_unavailable(
            self._knowledge_analytics, "v3.1 Knowledge Analytics not configured"
        )

    def operations_intelligence_preview(self) -> dict[str, Any]:
        """Return v3.1 operations observations without runtime automation."""

        return _dto_or_unavailable(
            self._operations_intelligence, "v3.1 Operations Intelligence not configured"
        )

    def developer_experience_preview(self) -> dict[str, Any]:
        """Return v3.1 developer guidance without modifying the workspace."""

        return _dto_or_unavailable(
            self._developer_experience, "v3.1 Developer Experience not configured"
        )

    def workflow_efficiency_preview(self) -> dict[str, Any]:
        """Return one-Page efficiency evidence without dispatching work."""

        return _dto_or_unavailable(
            self._workflow_efficiency, "v3.1 Workflow Efficiency not configured"
        )

    def creative_governance_v31_preview(self) -> dict[str, Any]:
        """Return v3.1 governance diagnostics without approval or remediation."""

        return _dto_or_unavailable(
            self._creative_governance_v31, "v3.1 Creative Governance not configured"
        )

    def knowledge_reliability_preview(self) -> dict[str, Any]:
        """Return v3.1 read-only Knowledge reliability diagnostics."""

        return _dto_or_unavailable(
            self._knowledge_reliability, "v3.1 Knowledge Reliability not configured"
        )

    def operational_readiness_v31_preview(self) -> dict[str, Any]:
        """Return v3.1 readiness evidence without deployment."""

        return _dto_or_unavailable(
            self._operational_readiness_v31, "v3.1 Operational Readiness not configured"
        )

    def release_quality_preview(self) -> dict[str, Any]:
        """Return v3.1 release-quality evidence without authorizing a release."""

        return _dto_or_unavailable(self._release_quality, "v3.1 Release Quality not configured")

    def compatibility_validation_preview(self) -> dict[str, Any]:
        """Return compatibility evidence without changing a public interface."""

        return _dto_or_unavailable(
            self._compatibility_validation, "v3.1 Compatibility Validation not configured"
        )

    def creative_studio_v32_preview(self) -> dict[str, Any]:
        """Return v3.2 Studio planning evidence without executing a workflow."""

        return _dto_or_unavailable(self._creative_studio_v32, "v3.2 Creative Studio not configured")

    def asset_intelligence_v32_preview(self) -> dict[str, Any]:
        """Return redacted v3.2 Asset intelligence without repository writes."""

        return _dto_or_unavailable(
            self._asset_intelligence_v32, "v3.2 Asset Intelligence not configured"
        )

    def workflow_profiles_v32_preview(self) -> dict[str, Any]:
        """Return existing StateMachine profile evidence without transition."""

        return _dto_or_unavailable(
            self._workflow_profiles_v32, "v3.2 Workflow Profiles not configured"
        )

    def production_analytics_v32_preview(self) -> dict[str, Any]:
        """Return v3.2 Production analytics without runtime automation."""

        return _dto_or_unavailable(
            self._production_analytics_v32, "v3.2 Production Analytics not configured"
        )

    def workspace_dashboard_v32_preview(self) -> dict[str, Any]:
        """Return a combined v3.2 workspace dashboard DTO without writes."""

        return _dto_or_unavailable(
            self._workspace_dashboard_v32, "v3.2 Workspace Dashboard not configured"
        )

    def creative_workspace_v32_preview(self) -> dict[str, Any]:
        """Return v3.2 Workspace insight DTOs without task execution or approval."""

        return _dto_or_unavailable(
            self._creative_workspace_v32, "v3.2 Creative Workspace not configured"
        )

    def asset_analytics_v32_preview(self) -> dict[str, Any]:
        """Return v3.2 redacted Asset Analytics without repository writes."""

        return _dto_or_unavailable(self._asset_analytics_v32, "v3.2 Asset Analytics not configured")

    def workflow_intelligence_v32_preview(self) -> dict[str, Any]:
        """Return v3.2 Workflow Intelligence without changing a workflow."""

        return _dto_or_unavailable(
            self._workflow_intelligence_v32, "v3.2 Workflow Intelligence not configured"
        )

    def production_insights_v32_preview(self) -> dict[str, Any]:
        """Return v3.2 Production Insights without automation or release authority."""

        return _dto_or_unavailable(
            self._production_insights_v32, "v3.2 Production Insights not configured"
        )

    def pipeline_analysis_v32_preview(self) -> dict[str, Any]:
        """Return v3.2 Pipeline analysis without applying a profile."""

        return _dto_or_unavailable(
            self._pipeline_analysis_v32, "v3.2 Pipeline Analysis not configured"
        )

    def creative_reliability_v32_preview(self) -> dict[str, Any]:
        """Return v3.2 Creative reliability evidence without workflow execution."""

        return _dto_or_unavailable(
            self._creative_reliability_v32, "v3.2 Creative Reliability not configured"
        )

    def asset_governance_v32_preview(self) -> dict[str, Any]:
        """Return v3.2 Asset governance evidence without repository mutation."""

        return _dto_or_unavailable(
            self._asset_governance_v32, "v3.2 Asset Governance not configured"
        )

    def operational_intelligence_v32_preview(self) -> dict[str, Any]:
        """Return v3.2 operational intelligence without runtime control."""

        return _dto_or_unavailable(
            self._operational_intelligence_v32,
            "v3.2 Operational Intelligence not configured",
        )

    def release_readiness_v32_preview(self) -> dict[str, Any]:
        """Return v3.2 release readiness evidence without authorization."""

        return _dto_or_unavailable(
            self._release_readiness_v32, "v3.2 Release Readiness not configured"
        )

    def compatibility_validation_v32_preview(self) -> dict[str, Any]:
        """Return v3.2 compatibility evidence without altering a public API."""

        return _dto_or_unavailable(
            self._compatibility_validation_v32,
            "v3.2 Compatibility Validation not configured",
        )

    def production_pipeline_v33_preview(self) -> dict[str, Any]:
        """Return v3.3 pipeline evidence without workflow execution or publishing."""

        return _dto_or_unavailable(
            self._production_pipeline_v33, "v3.3 Production Pipeline not configured"
        )

    def quality_intelligence_v33_preview(self) -> dict[str, Any]:
        """Return v3.3 quality evidence without scoring or approval authority."""

        return _dto_or_unavailable(
            self._quality_intelligence_v33, "v3.3 Quality Intelligence not configured"
        )

    def asset_lifecycle_v33_preview(self) -> dict[str, Any]:
        """Return v3.3 Asset Lifecycle evidence without repository mutation."""

        return _dto_or_unavailable(self._asset_lifecycle_v33, "v3.3 Asset Lifecycle not configured")

    def project_intelligence_v33_preview(self) -> dict[str, Any]:
        """Return v3.3 Project Intelligence without scheduling or allocation."""

        return _dto_or_unavailable(
            self._project_intelligence_v33, "v3.3 Project Intelligence not configured"
        )

    def production_intelligence_v33_preview(self) -> dict[str, Any]:
        """Return v3.3 Production Intelligence without workflow modification."""

        return _dto_or_unavailable(
            self._production_intelligence_v33, "v3.3 Production Intelligence not configured"
        )

    def quality_analytics_v33_preview(self) -> dict[str, Any]:
        """Return v3.3 Quality Analytics without scoring or approval authority."""

        return _dto_or_unavailable(
            self._quality_analytics_v33, "v3.3 Quality Analytics not configured"
        )

    def asset_intelligence_v33_preview(self) -> dict[str, Any]:
        """Return v3.3 Asset Intelligence without repository mutation."""

        return _dto_or_unavailable(
            self._asset_intelligence_v33, "v3.3 Asset Intelligence not configured"
        )

    def project_operations_v33_preview(self) -> dict[str, Any]:
        """Return v3.3 Project Operations without scheduling or allocation."""

        return _dto_or_unavailable(
            self._project_operations_v33, "v3.3 Project Operations not configured"
        )

    def production_governance_v33_preview(self) -> dict[str, Any]:
        """Return v3.3 Production Governance without policy enforcement."""

        return _dto_or_unavailable(
            self._production_governance_v33, "v3.3 Production Governance not configured"
        )

    def quality_governance_v33_preview(self) -> dict[str, Any]:
        """Return v3.3 Quality Governance without approval authority."""

        return _dto_or_unavailable(
            self._quality_governance_v33, "v3.3 Quality Governance not configured"
        )

    def asset_governance_v33_preview(self) -> dict[str, Any]:
        """Return v3.3 Asset Governance without retention or mutation."""

        return _dto_or_unavailable(
            self._asset_governance_v33, "v3.3 Asset Governance not configured"
        )

    def project_governance_v33_preview(self) -> dict[str, Any]:
        """Return v3.3 Project Governance without scheduling or allocation."""

        return _dto_or_unavailable(
            self._project_governance_v33, "v3.3 Project Governance not configured"
        )

    def knowledge_platform_v34_preview(self) -> dict[str, Any]:
        """Return v3.4 Knowledge Platform evidence without repository mutation."""

        return _dto_or_unavailable(
            self._knowledge_platform_v34, "v3.4 Knowledge Platform not configured"
        )

    def production_operations_v34_preview(self) -> dict[str, Any]:
        """Return v3.4 Production Operations without monitoring or deployment."""

        return _dto_or_unavailable(
            self._production_operations_v34, "v3.4 Production Operations not configured"
        )

    def organization_intelligence_v34_preview(self) -> dict[str, Any]:
        """Return v3.4 Organization Intelligence without personnel action."""

        return _dto_or_unavailable(
            self._organization_intelligence_v34,
            "v3.4 Organization Intelligence not configured",
        )

    def release_intelligence_v34_preview(self) -> dict[str, Any]:
        """Return v3.4 Release Intelligence without publication authority."""

        return _dto_or_unavailable(
            self._release_intelligence_v34, "v3.4 Release Intelligence not configured"
        )

    def knowledge_intelligence_v34_preview(self) -> dict[str, Any]:
        """Return v3.4 Knowledge Intelligence without repository mutation."""

        return _dto_or_unavailable(
            self._knowledge_intelligence_v34, "v3.4 Knowledge Intelligence not configured"
        )

    def production_optimization_v34_preview(self) -> dict[str, Any]:
        """Return v3.4 Production Optimization without workflow modification."""

        return _dto_or_unavailable(
            self._production_optimization_v34,
            "v3.4 Production Optimization not configured",
        )

    def organization_analytics_v34_preview(self) -> dict[str, Any]:
        """Return v3.4 Organization Analytics without personnel action."""

        return _dto_or_unavailable(
            self._organization_analytics_v34, "v3.4 Organization Analytics not configured"
        )

    def release_analytics_v34_preview(self) -> dict[str, Any]:
        """Return v3.4 Release Analytics without release authority."""

        return _dto_or_unavailable(
            self._release_analytics_v34, "v3.4 Release Analytics not configured"
        )

    def knowledge_governance_v34_preview(self) -> dict[str, Any]:
        """Return v3.4 Knowledge Governance without repository mutation."""

        return _dto_or_unavailable(
            self._knowledge_governance_v34, "v3.4 Knowledge Governance not configured"
        )

    def production_governance_v34_preview(self) -> dict[str, Any]:
        """Return v3.4 Production Governance without pipeline modification."""

        return _dto_or_unavailable(
            self._production_governance_v34, "v3.4 Production Governance not configured"
        )

    def organization_governance_v34_preview(self) -> dict[str, Any]:
        """Return v3.4 Organization Governance without personnel action."""

        return _dto_or_unavailable(
            self._organization_governance_v34, "v3.4 Organization Governance not configured"
        )

    def release_governance_v34_preview(self) -> dict[str, Any]:
        """Return v3.4 Release Governance without release authority."""

        return _dto_or_unavailable(
            self._release_governance_v34, "v3.4 Release Governance not configured"
        )

    def knowledge_graph_v35_preview(self) -> dict[str, Any]:
        """Return v3.5 Knowledge Graph evidence without graph persistence."""

        return _dto_or_unavailable(self._knowledge_graph_v35, "v3.5 Knowledge Graph not configured")

    def creative_intelligence_v35_preview(self) -> dict[str, Any]:
        """Return v3.5 Creative Intelligence without generation or approval."""

        return _dto_or_unavailable(
            self._creative_intelligence_v35, "v3.5 Creative Intelligence not configured"
        )

    def production_intelligence_v35_preview(self) -> dict[str, Any]:
        """Return v3.5 Production Intelligence without operational authority."""

        return _dto_or_unavailable(
            self._production_intelligence_v35, "v3.5 Production Intelligence not configured"
        )

    def platform_analytics_v35_preview(self) -> dict[str, Any]:
        """Return v3.5 Platform Analytics without collection or external action."""

        return _dto_or_unavailable(
            self._platform_analytics_v35, "v3.5 Platform Analytics not configured"
        )

    def knowledge_insights_v35_preview(self) -> dict[str, Any]:
        """Return v3.5 Knowledge Analytics without graph mutation."""

        return _dto_or_unavailable(
            self._knowledge_insights_v35, "v3.5 Knowledge Insights not configured"
        )

    def creative_analytics_v35_preview(self) -> dict[str, Any]:
        """Return v3.5 Creative Analytics without generation or approval."""

        return _dto_or_unavailable(
            self._creative_analytics_v35, "v3.5 Creative Analytics not configured"
        )

    def production_analytics_v35_preview(self) -> dict[str, Any]:
        """Return v3.5 Production Analytics without scheduling or deployment."""

        return _dto_or_unavailable(
            self._production_analytics_v35, "v3.5 Production Analytics not configured"
        )

    def executive_analytics_v35_preview(self) -> dict[str, Any]:
        """Return v3.5 Executive Analytics without collection or external action."""

        return _dto_or_unavailable(
            self._executive_analytics_v35, "v3.5 Executive Analytics not configured"
        )

    def knowledge_governance_v35_preview(self) -> dict[str, Any]:
        return _dto_or_unavailable(
            self._knowledge_governance_v35, "v3.5 Knowledge Governance not configured"
        )

    def creative_governance_v35_preview(self) -> dict[str, Any]:
        return _dto_or_unavailable(
            self._creative_governance_v35, "v3.5 Creative Governance not configured"
        )

    def production_governance_v35_preview(self) -> dict[str, Any]:
        return _dto_or_unavailable(
            self._production_governance_v35, "v3.5 Production Governance not configured"
        )

    def platform_governance_v35_preview(self) -> dict[str, Any]:
        return _dto_or_unavailable(
            self._platform_governance_v35, "v3.5 Platform Governance not configured"
        )


def create_observability_app(application: ObservabilityApplication) -> Any:
    """Create optional FastAPI delivery routes when the ``api`` extra is installed."""

    try:
        from fastapi import FastAPI
    except ImportError as exc:  # pragma: no cover - depends on optional extra.
        raise RuntimeError("Install manga-director[api] to enable FastAPI routes.") from exc
    app = FastAPI(title="manga-director observability", version=__version__)
    app.get("/health")(application.health_summary)
    app.get("/health/providers")(application.provider_health)
    app.get("/health/backends")(application.backend_health)
    app.get("/diagnostics")(application.diagnostics_report)
    app.get("/repository/check")(application.repository_integrity)
    app.get("/planning")(application.planning_preview)
    app.get("/planning/providers")(application.provider_preview)
    app.get("/analytics/workflow")(application.workflow_analytics)
    app.get("/analytics/enterprise")(application.enterprise_diagnostics)
    app.get("/analytics/executive")(application.executive_analytics)
    app.get("/assurance/workflow")(application.workflow_assurance)
    app.get("/assurance/providers")(application.provider_governance)
    app.get("/assurance/dashboard")(application.executive_dashboard)
    app.get("/director")(application.director_preview)
    app.get("/director/knowledge")(application.knowledge_preview)
    app.get("/director/orchestration")(application.orchestration_preview)
    app.get("/director/analysis")(application.director_analysis_preview)
    app.get("/director/dashboard")(application.optimization_dashboard_preview)
    app.get("/director/reliability")(application.director_reliability_preview)
    app.get("/director/governance")(application.knowledge_governance_preview)
    app.get("/director/readiness")(application.enterprise_ai_readiness_preview)
    app.get("/director/diagnostics")(application.ai_workflow_diagnostics_preview)
    app.get("/director/executive")(application.director_dashboard_preview)
    app.get("/v3/director")(application.director_platform_preview)
    app.get("/v3/creative")(application.creative_planning_preview)
    app.get("/v3/knowledge")(application.knowledge_foundation_preview)
    app.get("/v3/workflow")(application.workflow_intelligence_preview)
    app.get("/v3/summary")(application.planning_foundation_summary_preview)
    app.get("/v3/agents")(application.multi_agent_preview)
    app.get("/v3/creative-knowledge")(application.creative_knowledge_preview)
    app.get("/v3/director-intelligence")(application.director_intelligence_preview)
    app.get("/v3/review")(application.review_pipeline_preview)
    app.get("/v3/knowledge-relationships")(application.knowledge_relationship_preview)
    app.get("/v3/reliability")(application.director_reliability_v3_preview)
    app.get("/v3/governance")(application.creative_governance_preview)
    app.get("/v3/knowledge-integrity")(application.knowledge_integrity_preview)
    app.get("/v3/production-readiness")(application.production_readiness_preview)
    app.get("/v3/release-readiness")(application.release_readiness_preview)
    app.get("/v3.1/collaboration")(application.collaboration_foundation_preview)
    app.get("/v3.1/knowledge-evolution")(application.knowledge_evolution_preview)
    app.get("/v3.1/operations")(application.operations_foundation_preview)
    app.get("/v3.1/developer-productivity")(application.developer_productivity_preview)
    app.get("/v3.1/project-metrics")(application.project_metrics_preview)
    app.get("/v3.1/creative-review")(application.creative_review_preview)
    app.get("/v3.1/knowledge-analytics")(application.knowledge_analytics_preview)
    app.get("/v3.1/operations-intelligence")(application.operations_intelligence_preview)
    app.get("/v3.1/developer-experience")(application.developer_experience_preview)
    app.get("/v3.1/workflow-efficiency")(application.workflow_efficiency_preview)
    app.get("/v3.1/creative-governance")(application.creative_governance_v31_preview)
    app.get("/v3.1/knowledge-reliability")(application.knowledge_reliability_preview)
    app.get("/v3.1/operational-readiness")(application.operational_readiness_v31_preview)
    app.get("/v3.1/release-quality")(application.release_quality_preview)
    app.get("/v3.1/compatibility-validation")(application.compatibility_validation_preview)
    app.get("/v3.2/creative-studio")(application.creative_studio_v32_preview)
    app.get("/v3.2/asset-intelligence")(application.asset_intelligence_v32_preview)
    app.get("/v3.2/workflow-profiles")(application.workflow_profiles_v32_preview)
    app.get("/v3.2/production-analytics")(application.production_analytics_v32_preview)
    app.get("/v3.2/workspace-dashboard")(application.workspace_dashboard_v32_preview)
    app.get("/v3.2/creative-workspace")(application.creative_workspace_v32_preview)
    app.get("/v3.2/asset-analytics")(application.asset_analytics_v32_preview)
    app.get("/v3.2/workflow-intelligence")(application.workflow_intelligence_v32_preview)
    app.get("/v3.2/production-insights")(application.production_insights_v32_preview)
    app.get("/v3.2/pipeline-analysis")(application.pipeline_analysis_v32_preview)
    app.get("/v3.2/creative-reliability")(application.creative_reliability_v32_preview)
    app.get("/v3.2/asset-governance")(application.asset_governance_v32_preview)
    app.get("/v3.2/operational-intelligence")(application.operational_intelligence_v32_preview)
    app.get("/v3.2/release-readiness")(application.release_readiness_v32_preview)
    app.get("/v3.2/compatibility-validation")(application.compatibility_validation_v32_preview)
    app.get("/v3.3/production-pipeline")(application.production_pipeline_v33_preview)
    app.get("/v3.3/quality-intelligence")(application.quality_intelligence_v33_preview)
    app.get("/v3.3/asset-lifecycle")(application.asset_lifecycle_v33_preview)
    app.get("/v3.3/project-intelligence")(application.project_intelligence_v33_preview)
    app.get("/v3.3/production-intelligence")(application.production_intelligence_v33_preview)
    app.get("/v3.3/quality-analytics")(application.quality_analytics_v33_preview)
    app.get("/v3.3/asset-intelligence")(application.asset_intelligence_v33_preview)
    app.get("/v3.3/project-operations")(application.project_operations_v33_preview)
    app.get("/v3.3/production-governance")(application.production_governance_v33_preview)
    app.get("/v3.3/quality-governance")(application.quality_governance_v33_preview)
    app.get("/v3.3/asset-governance")(application.asset_governance_v33_preview)
    app.get("/v3.3/project-governance")(application.project_governance_v33_preview)
    app.get("/v3.4/knowledge-platform")(application.knowledge_platform_v34_preview)
    app.get("/v3.4/production-operations")(application.production_operations_v34_preview)
    app.get("/v3.4/organization-intelligence")(application.organization_intelligence_v34_preview)
    app.get("/v3.4/release-intelligence")(application.release_intelligence_v34_preview)
    app.get("/v3.4/knowledge-intelligence")(application.knowledge_intelligence_v34_preview)
    app.get("/v3.4/production-optimization")(application.production_optimization_v34_preview)
    app.get("/v3.4/organization-analytics")(application.organization_analytics_v34_preview)
    app.get("/v3.4/release-analytics")(application.release_analytics_v34_preview)
    app.get("/v3.4/knowledge-governance")(application.knowledge_governance_v34_preview)
    app.get("/v3.4/production-governance")(application.production_governance_v34_preview)
    app.get("/v3.4/organization-governance")(application.organization_governance_v34_preview)
    app.get("/v3.4/release-governance")(application.release_governance_v34_preview)
    app.get("/v3.5/knowledge-graph")(application.knowledge_graph_v35_preview)
    app.get("/v3.5/creative-intelligence")(application.creative_intelligence_v35_preview)
    app.get("/v3.5/production-intelligence")(application.production_intelligence_v35_preview)
    app.get("/v3.5/platform-analytics")(application.platform_analytics_v35_preview)
    app.get("/v3.5/knowledge-insights")(application.knowledge_insights_v35_preview)
    app.get("/v3.5/creative-analytics")(application.creative_analytics_v35_preview)
    app.get("/v3.5/production-analytics")(application.production_analytics_v35_preview)
    app.get("/v3.5/executive-analytics")(application.executive_analytics_v35_preview)
    app.get("/v3.5/knowledge-governance")(application.knowledge_governance_v35_preview)
    app.get("/v3.5/creative-governance")(application.creative_governance_v35_preview)
    app.get("/v3.5/production-governance")(application.production_governance_v35_preview)
    app.get("/v3.5/platform-governance")(application.platform_governance_v35_preview)
    return app


def _dto_or_unavailable(provider: Callable[[], Any] | None, reason: str) -> dict[str, Any]:
    if provider is None:
        return {"available": False, "reason": reason}
    value = provider()
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else dict(value)
