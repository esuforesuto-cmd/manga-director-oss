from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import typer

from manga_director.cli.config import (
    configuration_diagnostics,
    configuration_governance,
    load_config,
    write_default_config,
)
from manga_director.cli.runtime import CliRuntime, build_runtime
from manga_director.domain.exceptions import MangaDirectorError
from manga_director.mcp import McpServer, build_mcp_server
from manga_director.observability import (
    HealthMonitor,
    MetricsRegistry,
    RuntimeDiagnosticReport,
    RuntimeDiagnostics,
    RuntimeHealth,
    SystemHealthDashboard,
)
from manga_director.plugins import PluginManager
from manga_director.production import (
    AnalyticsService,
    AssuranceService,
    CollaborationPlanningService,
    DirectorFoundationService,
    DirectorPlanningService,
    DirectorReliabilityService,
    EnterpriseDiagnostics,
    EnterpriseReadiness,
    KnowledgeIntelligenceService,
    KnowledgeService,
    OperationalAnalytics,
    PlanningService,
    ProviderGovernance,
    ProviderOptimizer,
    ProviderOrchestrator,
    RepositoryMaintenance,
    V3ReadinessService,
    V31AssuranceService,
    V31FoundationService,
    V31InsightsService,
    V32AssuranceService,
    V32FoundationService,
    V32InsightsService,
    V33FoundationService,
    V33GovernanceService,
    V33InsightsService,
    V34FoundationService,
    V34GovernanceService,
    V34InsightsService,
    V35FoundationService,
    V35GovernanceService,
    V35InsightsService,
    WorkflowDependencyAnalyzer,
    WorkflowPlanner,
    WorkflowReliabilityAnalyzer,
)
from manga_director.repositories import RepositorySelfCheck
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.protocols import ProjectRepository
from manga_director.sdk import ExtensionValidator
from manga_director.workflow import WorkflowContext
from manga_director.workflow.durable_execution import _route_localfile_primary, _route_localfile_run

app = typer.Typer(help="Headless, one-page-at-a-time manga production workflow engine.")
project_app = typer.Typer(help="Create, inspect, transfer, and delete persisted projects.")
chapter_app = typer.Typer(help="Run and inspect sequential page workflows within a chapter.")
batch_app = typer.Typer(help="Plan and run persisted, sequential batches of page workflows.")
mcp_app = typer.Typer(help="Run the local stdio MCP server and inspect its surface.")
plugin_app = typer.Typer(help="Discover and administer local, manifest-based plugins.")
diagnostics_app = typer.Typer(help="Inspect runtime health and export safe diagnostic DTOs.")
health_app = typer.Typer(help="Run transport-neutral runtime health checks.")
repository_app = typer.Typer(help="Run read-only repository integrity checks.")
provider_app = typer.Typer(help="Inspect local LLM provider health.")
backend_app = typer.Typer(help="Inspect local image backend health.")
planning_app = typer.Typer(help="Preview read-only workflow and Provider planning DTOs.")
analytics_app = typer.Typer(help="Analyze one workflow and runtime metadata without execution.")
assurance_app = typer.Typer(help="Review AI workflow reliability and readiness without execution.")
director_app = typer.Typer(help="Preview read-only AI Director, Knowledge, and orchestration DTOs.")
app.add_typer(project_app, name="project")
app.add_typer(chapter_app, name="chapter")
app.add_typer(batch_app, name="batch")
app.add_typer(mcp_app, name="mcp")
app.add_typer(plugin_app, name="plugin")
app.add_typer(diagnostics_app, name="diagnostics")
app.add_typer(health_app, name="health")
app.add_typer(repository_app, name="repository")
app.add_typer(provider_app, name="provider")
app.add_typer(backend_app, name="backend")
app.add_typer(planning_app, name="planning")
app.add_typer(analytics_app, name="analytics")
app.add_typer(assurance_app, name="assurance")
app.add_typer(director_app, name="director")
LOGGER = logging.getLogger(__name__)


def _runtime(config_path: Path, *, create_config: bool = False) -> CliRuntime:
    config = write_default_config(config_path) if create_config else load_config(config_path)
    return build_runtime(config, config_path.parent)


def _plugin_manager(config_path: Path, *, create_config: bool = False) -> PluginManager:
    config = write_default_config(config_path) if create_config else load_config(config_path)
    directory = config.plugin_directory
    if not directory.is_absolute():
        directory = config_path.parent / directory
    return PluginManager(directory)


def _use_runtime(
    config_path: Path,
    action: Callable[[CliRuntime], None],
    *,
    create_config: bool = False,
) -> None:
    """Run one CLI operation and always complete the active plugin lifecycle."""
    runtime = _runtime(config_path, create_config=create_config)
    try:
        action(runtime)
    finally:
        runtime.plugins.shutdown()


def _emit(value: Any) -> None:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    elif isinstance(value, list):
        value = [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item for item in value
        ]
    typer.echo(json.dumps(value, ensure_ascii=False, indent=2))


def _with_metadata(context: WorkflowContext, values: dict[str, Any]) -> WorkflowContext:
    return context.model_copy(update={"metadata": {**context.metadata, **values}}, deep=True)


def _handle_error(logger: logging.Logger, action: Callable[[], None]) -> None:
    try:
        action()
    except (MangaDirectorError, ValueError, OSError) as exc:
        logger.exception("Workflow exception")
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


def _mcp_server(runtime: CliRuntime, config_path: Path) -> McpServer:
    return build_mcp_server(
        workflow_engine=runtime.engine,
        workflow_coordinator=runtime.coordinator,
        project_loader=runtime.loader,
        repository=runtime.loader.repository,
        prompt_directory=runtime.prompt_directory,
        configuration=runtime.config,
        diagnostics_provider=lambda: _runtime_report(runtime, config_path),
        health_provider=lambda: _health_dashboard(runtime, config_path),
        provider_health_provider=lambda: _runtime_health(runtime, config_path).report().provider,
        backend_health_provider=lambda: _runtime_health(runtime, config_path).report().backend,
        repository_check_provider=lambda: RepositorySelfCheck(runtime.loader.repository).check(),
        planning_provider=lambda: _planning_service(runtime).summary(
            WorkflowContext(page={"id": "mcp-planning-preview"}),
            configuration=runtime.config.model_dump(mode="json"),
        ),
        provider_selection_provider=lambda: _planning_service(runtime).provider_preview(),
        analytics_provider=lambda: _analytics_service(runtime).workflow_analysis(
            WorkflowContext(page={"id": "mcp-analytics-preview"})
        ),
        enterprise_provider=lambda: _analytics_service(runtime).enterprise_diagnostics(
            WorkflowContext(page={"id": "mcp-enterprise-preview"})
        ),
        executive_provider=lambda: _analytics_service(runtime).executive_report(
            WorkflowContext(page={"id": "mcp-executive-preview"})
        ),
        assurance_provider=lambda: _assurance_service(runtime).workflow_reliability(
            WorkflowContext(page={"id": "mcp-assurance-preview"})
        ),
        provider_governance_provider=lambda: _assurance_service(runtime).provider_governance(),
        dashboard_provider=lambda: _assurance_service(runtime).dashboard(
            WorkflowContext(page={"id": "mcp-dashboard-preview"})
        ),
        director_provider=lambda: _director_service(runtime).director_plan(
            WorkflowContext(page={"id": "mcp-director-preview"})
        ),
        knowledge_provider=lambda: _director_service(runtime).knowledge_report(),
        orchestration_provider=lambda: _director_service(runtime).orchestration(
            WorkflowContext(page={"id": "mcp-orchestration-preview"})
        ),
        director_reliability_provider=lambda: _director_reliability_service(
            runtime
        ).director_reliability(WorkflowContext(page={"id": "mcp-director-reliability"})),
        knowledge_governance_provider=lambda: _director_reliability_service(
            runtime
        ).knowledge_governance(),
        enterprise_ai_readiness_provider=lambda: _director_reliability_service(
            runtime
        ).enterprise_ai_readiness(WorkflowContext(page={"id": "mcp-enterprise-ai"})),
        ai_workflow_diagnostics_provider=lambda: _director_reliability_service(runtime).diagnostics(
            WorkflowContext(page={"id": "mcp-ai-workflow-diagnostics"})
        ),
        director_dashboard_provider=lambda: _director_reliability_service(runtime).dashboard(
            WorkflowContext(page={"id": "mcp-director-dashboard"})
        ),
        director_platform_provider=lambda: _director_platform_service(runtime).director_platform(
            WorkflowContext(page={"id": "mcp-v3-director-platform"})
        ),
        creative_planning_provider=lambda: _director_platform_service(runtime).creative_dashboard(
            WorkflowContext(page={"id": "mcp-v3-creative-planning"})
        ),
        knowledge_foundation_provider=lambda: _director_platform_service(
            runtime
        ).knowledge_dashboard(),
        workflow_intelligence_provider=lambda: _director_platform_service(
            runtime
        ).workflow_dashboard(WorkflowContext(page={"id": "mcp-v3-workflow-intelligence"})),
        planning_summary_provider=lambda: _director_platform_service(runtime).planning_summary(
            WorkflowContext(page={"id": "mcp-v3-planning-summary"})
        ),
        multi_agent_provider=lambda: _collaboration_service(runtime).agent_dashboard(
            WorkflowContext(page={"id": "mcp-v3-multi-agent"})
        ),
        creative_knowledge_provider=lambda: _collaboration_service(
            runtime
        ).creative_knowledge_dashboard(),
        director_intelligence_provider=lambda: _collaboration_service(
            runtime
        ).director_intelligence_dashboard(
            WorkflowContext(page={"id": "mcp-v3-director-intelligence"})
        ),
        review_pipeline_provider=lambda: _collaboration_service(runtime).review_pipeline_dashboard(
            WorkflowContext(page={"id": "mcp-v3-review-pipeline"})
        ),
        knowledge_relationship_provider=lambda: (
            _collaboration_service(runtime).creative_knowledge().relationships
        ),
        director_reliability_v3_provider=lambda: _v3_readiness_service(runtime).director_executive(
            WorkflowContext(page={"id": "mcp-v3-director-reliability"})
        ),
        creative_governance_provider=lambda: _v3_readiness_service(runtime).creative_executive(
            WorkflowContext(page={"id": "mcp-v3-creative-governance"})
        ),
        knowledge_integrity_provider=lambda: _v3_readiness_service(runtime).knowledge_executive(),
        production_readiness_provider=lambda: _v3_readiness_service(runtime).production_executive(
            WorkflowContext(page={"id": "mcp-v3-production-readiness"}),
            runtime.config.model_dump(mode="json"),
        ),
        release_readiness_provider=lambda: _v3_readiness_service(runtime).release_dashboard(
            WorkflowContext(page={"id": "mcp-v3-release-readiness"}),
            runtime.config.model_dump(mode="json"),
        ),
        collaboration_foundation_provider=lambda: _v31_foundation_service(
            runtime
        ).collaboration_dashboard(WorkflowContext(page={"id": "mcp-v31-collaboration"})),
        knowledge_evolution_provider=lambda: _v31_foundation_service(
            runtime
        ).knowledge_evolution_dashboard(),
        operations_foundation_provider=lambda: _v31_foundation_service(
            runtime
        ).operations_dashboard(WorkflowContext(page={"id": "mcp-v31-operations"})),
        developer_productivity_provider=lambda: _v31_foundation_service(
            runtime
        ).developer_productivity_dashboard(),
        project_metrics_provider=lambda: (
            _v31_foundation_service(runtime)
            .operations_dashboard(WorkflowContext(page={"id": "mcp-v31-project-metrics"}))
            .report.project
        ),
        creative_review_provider=lambda: _v31_insights_service(runtime).creative_review_dashboard(
            WorkflowContext(page={"id": "mcp-v31-creative-review"})
        ),
        knowledge_analytics_provider=lambda: _v31_insights_service(
            runtime
        ).knowledge_analytics_dashboard(),
        operations_intelligence_provider=lambda: _v31_insights_service(
            runtime
        ).operations_intelligence_dashboard(
            WorkflowContext(page={"id": "mcp-v31-operations-intelligence"})
        ),
        developer_experience_provider=lambda: _v31_insights_service(
            runtime
        ).developer_experience_dashboard(runtime.config.model_dump(mode="json")),
        workflow_efficiency_provider=lambda: (
            _v31_insights_service(runtime)
            .operations_intelligence_dashboard(
                WorkflowContext(page={"id": "mcp-v31-workflow-efficiency"})
            )
            .report.workflow_efficiency
        ),
        creative_governance_v31_provider=lambda: _v31_assurance_service(
            runtime
        ).creative_governance_dashboard(
            WorkflowContext(page={"id": "mcp-v31-creative-governance"})
        ),
        knowledge_reliability_provider=lambda: _v31_assurance_service(
            runtime
        ).knowledge_reliability_dashboard(),
        operational_readiness_v31_provider=lambda: _v31_assurance_service(
            runtime
        ).operational_readiness_dashboard(
            WorkflowContext(page={"id": "mcp-v31-operational-readiness"}),
            runtime.config.model_dump(mode="json"),
        ),
        release_quality_provider=lambda: _v31_assurance_service(runtime).release_quality_dashboard(
            WorkflowContext(page={"id": "mcp-v31-release-quality"}),
            runtime.config.model_dump(mode="json"),
        ),
        compatibility_validation_provider=lambda: (
            _v31_assurance_service(runtime)
            .release_quality_dashboard(
                WorkflowContext(page={"id": "mcp-v31-compatibility"}),
                runtime.config.model_dump(mode="json"),
            )
            .report.compatibility
        ),
        creative_studio_v32_provider=lambda: _v32_foundation_service(
            runtime
        ).creative_studio_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v32-creative-studio"})
        ),
        asset_intelligence_v32_provider=lambda: _v32_foundation_service(
            runtime
        ).asset_intelligence_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v32-asset-intelligence"})
        ),
        workflow_profiles_v32_provider=lambda: _v32_foundation_service(
            runtime
        ).workflow_profile_dashboard(WorkflowContext(page={"id": "mcp-v32-workflow-profiles"})),
        production_analytics_v32_provider=lambda: _v32_foundation_service(
            runtime
        ).production_analytics_dashboard(
            WorkflowContext(page={"id": "mcp-v32-production-analytics"})
        ),
        workspace_dashboard_v32_provider=lambda: _v32_foundation_service(
            runtime
        ).creative_studio_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v32-workspace-dashboard"})
        ),
        creative_workspace_v32_provider=lambda: _v32_insights_service(
            runtime
        ).creative_workspace_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v32-creative-workspace"})
        ),
        asset_analytics_v32_provider=lambda: _v32_insights_service(
            runtime
        ).asset_analytics_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v32-asset-analytics"})
        ),
        workflow_intelligence_v32_provider=lambda: _v32_insights_service(
            runtime
        ).workflow_intelligence_dashboard(
            WorkflowContext(page={"id": "mcp-v32-workflow-intelligence"})
        ),
        production_insights_v32_provider=lambda: _v32_insights_service(
            runtime
        ).production_insights_dashboard(
            WorkflowContext(page={"id": "mcp-v32-production-insights"})
        ),
        pipeline_analysis_v32_provider=lambda: _v32_insights_service(
            runtime
        ).workflow_intelligence_dashboard(
            WorkflowContext(page={"id": "mcp-v32-pipeline-analysis"})
        ),
        creative_reliability_v32_provider=lambda: _v32_assurance_service(
            runtime
        ).creative_reliability_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v32-creative-reliability"})
        ),
        asset_governance_v32_provider=lambda: _v32_assurance_service(
            runtime
        ).asset_governance_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v32-asset-governance"})
        ),
        operational_intelligence_v32_provider=lambda: _v32_assurance_service(
            runtime
        ).operational_intelligence_dashboard(
            WorkflowContext(page={"id": "mcp-v32-operational-intelligence"})
        ),
        release_readiness_v32_provider=lambda: _v32_assurance_service(
            runtime
        ).release_readiness_dashboard(WorkflowContext(page={"id": "mcp-v32-release-readiness"})),
        compatibility_validation_v32_provider=lambda: (
            _v32_assurance_service(runtime)
            .release_readiness_dashboard(WorkflowContext(page={"id": "mcp-v32-compatibility"}))
            .report.compatibility
        ),
        production_pipeline_v33_provider=lambda: _v33_foundation_service(
            runtime
        ).production_pipeline_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v33-production-pipeline"})
        ),
        quality_intelligence_v33_provider=lambda: _v33_foundation_service(
            runtime
        ).quality_intelligence_dashboard(
            WorkflowContext(page={"id": "mcp-v33-quality-intelligence"})
        ),
        asset_lifecycle_v33_provider=lambda: _v33_foundation_service(
            runtime
        ).asset_lifecycle_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v33-asset-lifecycle"})
        ),
        project_intelligence_v33_provider=lambda: _v33_foundation_service(
            runtime
        ).project_intelligence_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v33-project-intelligence"})
        ),
        production_intelligence_v33_provider=lambda: _v33_insights_service(
            runtime
        ).production_intelligence_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v33-production-intelligence"})
        ),
        quality_analytics_v33_provider=lambda: _v33_insights_service(
            runtime
        ).quality_analytics_dashboard(WorkflowContext(page={"id": "mcp-v33-quality-analytics"})),
        asset_intelligence_v33_provider=lambda: _v33_insights_service(
            runtime
        ).asset_intelligence_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v33-asset-intelligence"})
        ),
        project_operations_v33_provider=lambda: _v33_insights_service(
            runtime
        ).project_operations_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v33-project-operations"})
        ),
        production_governance_v33_provider=lambda: _v33_governance_service(
            runtime
        ).production_governance_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v33-production-governance"})
        ),
        quality_governance_v33_provider=lambda: _v33_governance_service(
            runtime
        ).quality_governance_dashboard(WorkflowContext(page={"id": "mcp-v33-quality-governance"})),
        asset_governance_v33_provider=lambda: _v33_governance_service(
            runtime
        ).asset_governance_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v33-asset-governance"})
        ),
        project_governance_v33_provider=lambda: _v33_governance_service(
            runtime
        ).project_governance_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v33-project-governance"})
        ),
        knowledge_platform_v34_provider=lambda: _v34_foundation_service(
            runtime
        ).knowledge_platform_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v34-knowledge-platform"})
        ),
        production_operations_v34_provider=lambda: _v34_foundation_service(
            runtime
        ).production_operations_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v34-production-operations"})
        ),
        organization_intelligence_v34_provider=lambda: _v34_foundation_service(
            runtime
        ).organization_intelligence_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v34-organization-intelligence"})
        ),
        release_intelligence_v34_provider=lambda: _v34_foundation_service(
            runtime
        ).release_intelligence_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v34-release-intelligence"})
        ),
        knowledge_intelligence_v34_provider=lambda: _v34_insights_service(
            runtime
        ).knowledge_intelligence_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v34-knowledge-intelligence"})
        ),
        production_optimization_v34_provider=lambda: _v34_insights_service(
            runtime
        ).production_optimization_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v34-production-optimization"})
        ),
        organization_analytics_v34_provider=lambda: _v34_insights_service(
            runtime
        ).organization_analytics_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v34-organization-analytics"})
        ),
        release_analytics_v34_provider=lambda: _v34_insights_service(
            runtime
        ).release_analytics_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v34-release-analytics"})
        ),
        knowledge_governance_v34_provider=lambda: _v34_governance_service(
            runtime
        ).knowledge_governance_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v34-knowledge-governance"})
        ),
        production_governance_v34_provider=lambda: _v34_governance_service(
            runtime
        ).production_governance_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v34-production-governance"})
        ),
        organization_governance_v34_provider=lambda: _v34_governance_service(
            runtime
        ).organization_governance_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v34-organization-governance"})
        ),
        release_governance_v34_provider=lambda: _v34_governance_service(
            runtime
        ).release_governance_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v34-release-governance"})
        ),
        knowledge_graph_v35_provider=lambda: _v35_foundation_service(
            runtime
        ).knowledge_graph_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v35-knowledge-graph"})
        ),
        creative_intelligence_v35_provider=lambda: _v35_foundation_service(
            runtime
        ).creative_intelligence_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v35-creative-intelligence"})
        ),
        production_intelligence_v35_provider=lambda: _v35_foundation_service(
            runtime
        ).production_intelligence_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v35-production-intelligence"})
        ),
        platform_analytics_v35_provider=lambda: _v35_foundation_service(
            runtime
        ).platform_analytics_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v35-platform-analytics"})
        ),
        knowledge_insights_v35_provider=lambda: _v35_insights_service(
            runtime
        ).knowledge_insights_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v35-knowledge-insights"})
        ),
        creative_analytics_v35_provider=lambda: _v35_insights_service(
            runtime
        ).creative_analytics_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v35-creative-analytics"})
        ),
        production_analytics_v35_provider=lambda: _v35_insights_service(
            runtime
        ).production_analytics_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v35-production-analytics"})
        ),
        executive_analytics_v35_provider=lambda: _v35_insights_service(
            runtime
        ).executive_analytics_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v35-executive-analytics"})
        ),
        knowledge_governance_v35_provider=lambda: _v35_governance_service(
            runtime
        ).knowledge_governance_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v35-knowledge-governance"})
        ),
        creative_governance_v35_provider=lambda: _v35_governance_service(
            runtime
        ).creative_governance_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v35-creative-governance"})
        ),
        production_governance_v35_provider=lambda: _v35_governance_service(
            runtime
        ).production_governance_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v35-production-governance"})
        ),
        platform_governance_v35_provider=lambda: _v35_governance_service(
            runtime
        ).platform_governance_dashboard(
            "mcp-preview", WorkflowContext(page={"id": "mcp-v35-platform-governance"})
        ),
    )


def _planning_service(runtime: CliRuntime) -> PlanningService:
    """Compose the passive planning facade without invoking an Agent or Provider."""

    return PlanningService(
        planner=WorkflowPlanner(), providers=ProviderOrchestrator(runtime.providers)
    )


def _analytics_service(runtime: CliRuntime) -> AnalyticsService:
    """Compose passive analytics from existing runtime metadata and Repository ports."""

    planning = _planning_service(runtime)
    workflow = WorkflowDependencyAnalyzer(planning)
    providers = ProviderOptimizer(runtime.providers, ProviderOrchestrator(runtime.providers))
    repository = RepositoryMaintenance(runtime.loader.repository)
    return AnalyticsService(
        workflow=workflow,
        providers=providers,
        enterprise=EnterpriseDiagnostics(
            configuration=runtime.config,
            workflow=workflow,
            providers=providers,
            backends=runtime.backends,
            repository=repository,
        ),
        operations=OperationalAnalytics(),
        repository=repository,
    )


def _assurance_service(runtime: CliRuntime) -> AssuranceService:
    """Compose read-only assurance helpers from the existing runtime boundaries."""

    planning = _planning_service(runtime)
    workflow = WorkflowReliabilityAnalyzer(planning, WorkflowDependencyAnalyzer(planning))
    providers = ProviderGovernance(
        runtime=runtime.providers,
        optimizer=ProviderOptimizer(runtime.providers, ProviderOrchestrator(runtime.providers)),
        configuration=runtime.config,
    )
    repository = RepositoryMaintenance(runtime.loader.repository)
    return AssuranceService(
        workflow=workflow,
        providers=providers,
        enterprise=EnterpriseReadiness(
            configuration=runtime.config,
            workflow=workflow,
            providers=providers,
            repository=repository,
        ),
        planning=planning,
        repository=repository,
    )


def _director_service(runtime: CliRuntime) -> DirectorFoundationService:
    """Compose advisory Director DTOs through the existing planning and repository ports."""

    return DirectorFoundationService(
        _planning_service(runtime), KnowledgeService(runtime.loader.repository)
    )


def _intelligence_service(runtime: CliRuntime) -> KnowledgeIntelligenceService:
    """Compose non-executing Knowledge Intelligence from existing application services."""

    return KnowledgeIntelligenceService(_director_service(runtime))


def _director_reliability_service(runtime: CliRuntime) -> DirectorReliabilityService:
    """Compose Director reliability evidence with no workflow execution capability."""

    foundation = _director_service(runtime)
    return DirectorReliabilityService(foundation, KnowledgeIntelligenceService(foundation))


def _director_platform_service(runtime: CliRuntime) -> DirectorPlanningService:
    """Compose v3 advisory foundation DTOs without adding workflow execution authority."""

    return DirectorPlanningService(_director_service(runtime), _planning_service(runtime))


def _collaboration_service(runtime: CliRuntime) -> CollaborationPlanningService:
    """Compose v3 collaboration reports without Agent execution or workflow authority."""

    return CollaborationPlanningService(_director_platform_service(runtime))


def _v3_readiness_service(runtime: CliRuntime) -> V3ReadinessService:
    """Compose v3 validation and readiness DTOs without deployment or workflow authority."""

    foundation = _director_platform_service(runtime)
    return V3ReadinessService(foundation, CollaborationPlanningService(foundation))


def _v31_foundation_service(runtime: CliRuntime) -> V31FoundationService:
    """Compose v3.1 DTO foundations without workflow, repository, or Agent authority."""

    foundation = _director_platform_service(runtime)
    return V31FoundationService(
        foundation,
        CollaborationPlanningService(foundation),
        runtime.loader.repository,
    )


def _v31_insights_service(runtime: CliRuntime) -> V31InsightsService:
    """Compose v3.1 analysis-only review and operations insights."""

    return V31InsightsService(_v31_foundation_service(runtime), runtime.loader.repository)


def _v31_assurance_service(runtime: CliRuntime) -> V31AssuranceService:
    """Compose v3.1 governance/readiness diagnostics without operational authority."""

    foundation = _v31_foundation_service(runtime)
    return V31AssuranceService(
        foundation,
        V31InsightsService(foundation, runtime.loader.repository),
        runtime.loader.repository,
    )


def _v32_foundation_service(runtime: CliRuntime) -> V32FoundationService:
    """Compose v3.2 read-only Studio, Asset, Profile, and Analytics DTOs."""

    return V32FoundationService(runtime.loader.repository)


def _v33_foundation_service(runtime: CliRuntime) -> V33FoundationService:
    """Compose v3.3 pipeline, quality, asset, and project DTOs without execution."""

    return V33FoundationService(runtime.loader.repository)


def _v34_foundation_service(runtime: CliRuntime) -> V34FoundationService:
    """Compose v3.4 knowledge and operational DTOs without execution authority."""

    return V34FoundationService(runtime.loader.repository)


def _v34_insights_service(runtime: CliRuntime) -> V34InsightsService:
    """Compose v3.4 advisory analysis DTOs without operational authority."""

    foundation = _v34_foundation_service(runtime)
    return V34InsightsService(foundation, runtime.loader.repository)


def _v34_governance_service(runtime: CliRuntime) -> V34GovernanceService:
    """Compose v3.4 audit and policy DTOs without enforcement authority."""

    foundation = _v34_foundation_service(runtime)
    insights = V34InsightsService(foundation, runtime.loader.repository)
    return V34GovernanceService(foundation, insights, runtime.loader.repository)


def _v35_foundation_service(runtime: CliRuntime) -> V35FoundationService:
    """Compose v3.5 DTO projections without graph, workflow, or operational authority."""

    return V35FoundationService(runtime.loader.repository)


def _v35_insights_service(runtime: CliRuntime) -> V35InsightsService:
    """Compose v3.5 analysis DTOs without applying recommendations or actions."""

    foundation = _v35_foundation_service(runtime)
    return V35InsightsService(foundation, runtime.loader.repository)


def _v35_governance_service(runtime: CliRuntime) -> V35GovernanceService:
    """Compose v3.5 policy and audit evidence without enforcement authority."""

    foundation = _v35_foundation_service(runtime)
    insights = V35InsightsService(foundation, runtime.loader.repository)
    return V35GovernanceService(foundation, insights, runtime.loader.repository)


def _v33_insights_service(runtime: CliRuntime) -> V33InsightsService:
    """Compose v3.3 analysis DTOs without execution, mutation, or approval authority."""

    foundation = _v33_foundation_service(runtime)
    return V33InsightsService(foundation, runtime.loader.repository)


def _v33_governance_service(runtime: CliRuntime) -> V33GovernanceService:
    """Compose v3.3 audit and policy DTOs without enforcement authority."""

    foundation = _v33_foundation_service(runtime)
    insights = V33InsightsService(foundation, runtime.loader.repository)
    return V33GovernanceService(foundation, insights, runtime.loader.repository)


def _v32_insights_service(runtime: CliRuntime) -> V32InsightsService:
    """Compose v3.2 analysis DTOs without execution, writes, or approval authority."""

    foundation = _v32_foundation_service(runtime)
    return V32InsightsService(foundation, runtime.loader.repository)


def _v32_assurance_service(runtime: CliRuntime) -> V32AssuranceService:
    """Compose v3.2 validation DTOs without execution, persistence, or release authority."""

    foundation = _v32_foundation_service(runtime)
    insights = V32InsightsService(foundation, runtime.loader.repository)
    return V32AssuranceService(foundation, insights, runtime.loader.repository)


def _runtime_report(runtime: CliRuntime, config_path: Path) -> RuntimeDiagnosticReport:
    repository = runtime.loader.repository
    metrics = getattr(getattr(repository, "metrics", None), "metrics", None)
    repository_snapshot = metrics.snapshot() if metrics is not None else {"configured": True}
    return RuntimeDiagnostics(MetricsRegistry()).report(
        plugins=runtime.plugins.diagnostics(),
        extensions=ExtensionValidator().diagnostics(),
        configuration=configuration_diagnostics(config_path),
        repositories=repository_snapshot,
        providers=runtime.providers.report().model_dump(),
        backends=runtime.backends.report().model_dump(),
        workflow={"healthy": True, "scope": "one_page"},
        events={"mode": "in_memory"},
    )


def _runtime_health(runtime: CliRuntime, config_path: Path) -> RuntimeHealth:
    return RuntimeHealth(
        config=runtime.config,
        providers=runtime.providers,
        backends=runtime.backends,
        repository_check=RepositorySelfCheck(runtime.loader.repository),
        workflow_check=lambda: runtime.engine is not None,
        plugin_check=lambda: _plugins_available(runtime.plugins),
        extension_check=lambda: bool(ExtensionValidator().diagnostics() is not None),
        plugin_details=runtime.plugins.diagnostics,
        extension_details=ExtensionValidator().diagnostics,
        configuration_summary=lambda: configuration_governance(runtime.config).model_dump(),
    )


def _health_dashboard(runtime: CliRuntime, config_path: Path) -> SystemHealthDashboard:
    repository = runtime.loader.repository
    monitor = HealthMonitor(
        {
            "configuration": lambda: load_config(config_path) == runtime.config,
            "repository": lambda: _repository_available(repository),
            "plugins": lambda: _plugins_available(runtime.plugins),
            "extension_sdk": lambda: bool(ExtensionValidator().diagnostics() is not None),
            "notification": lambda: True,
            "automation": lambda: True,
        }
    )
    plugin_diagnostics = runtime.plugins.diagnostics()
    active = cast(list[object], plugin_diagnostics.get("active", []))
    details: dict[str, dict[str, object]] = {
        "repository": {"type": type(repository).__name__},
        "plugins": {"active": len(active)},
        "extension_sdk": {"mode": "available"},
        "notification": {"mode": "not_configured"},
        "automation": {"mode": "not_configured"},
    }
    return monitor.dashboard(details)


def _repository_available(repository: ProjectRepository) -> bool:
    metadata = getattr(repository, "list_metadata", None)
    if callable(metadata):
        metadata(limit=1)
    else:
        repository.list()
    return True


def _plugins_available(manager: PluginManager) -> bool:
    manager.discover()
    return True


def _execute_primary(
    command: str,
    project: str,
    page: str,
    config_path: Path,
    metadata: dict[str, Any] | None = None,
) -> None:
    logger = LOGGER

    def action() -> None:
        def execute(runtime: CliRuntime) -> None:
            logger.info("Workflow start: %s %s/%s", command, project, page)
            repository = runtime.loader.repository
            if isinstance(repository, LocalFileRepository):
                composition = getattr(runtime, "localfile_external_generation", None)
                if composition is None:
                    result = _route_localfile_primary(
                        runtime.engine, repository, project, page, command, metadata or {}
                    )
                else:
                    result = _route_localfile_primary(
                        runtime.engine,
                        repository,
                        project,
                        page,
                        command,
                        metadata or {},
                        logical_output_asset_quality_gate=composition.quality_gate,
                    )
            else:
                context = _with_metadata(runtime.loader.load(project, page), metadata or {})
                result = runtime.engine.execute_command(context, command)
                runtime.loader.save(project, page, result.context)
            logger.info("State transition: %s", result.logs[0])
            logger.info("Workflow end: %s", command)
            _emit(result)

        _use_runtime(config_path, execute)

    _handle_error(logger, action)


def _execute_support(command: str, project: str, page: str, config_path: Path) -> None:
    logger = LOGGER

    def action() -> None:
        def execute(runtime: CliRuntime) -> None:
            logger.info("Workflow support start: %s %s/%s", command, project, page)
            result = runtime.engine.execute_support(runtime.loader.load(project, page), command)
            runtime.loader.save(project, page, result.context)
            logger.info("Workflow support end: %s", command)
            _emit(result)

        _use_runtime(config_path, execute)

    _handle_error(logger, action)


@app.command()
def init(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option(..., "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Initialize one Draft page and create config.yaml if needed."""
    logger = LOGGER

    def action() -> None:
        def execute(runtime: CliRuntime) -> None:
            logger.info("Workflow start: init %s/%s", project, page)
            context = runtime.loader.initialize(project, page)
            logger.info("Workflow end: init")
            _emit(context)

        _use_runtime(config, execute, create_config=True)

    _handle_error(logger, action)


@app.command()
def design(
    project: str,
    page: str,
    purpose: str = typer.Option("", "--purpose"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    metadata = {"page_design": {"purpose": purpose}} if purpose else {}
    _execute_primary("design", project, page, config, metadata)


@app.command()
def review(
    project: str, page: str, config: Path = typer.Option(Path("config.yaml"), "--config")
) -> None:
    _execute_primary("review", project, page, config)


@app.command()
def storyboard(
    project: str, page: str, config: Path = typer.Option(Path("config.yaml"), "--config")
) -> None:
    _execute_primary("storyboard", project, page, config)


@app.command()
def dialogue(
    project: str, page: str, config: Path = typer.Option(Path("config.yaml"), "--config")
) -> None:
    _execute_support("dialogue", project, page, config)


@app.command()
def prompt(
    project: str, page: str, config: Path = typer.Option(Path("config.yaml"), "--config")
) -> None:
    _execute_primary("prompt", project, page, config)


@app.command()
def generate(
    project: str, page: str, config: Path = typer.Option(Path("config.yaml"), "--config")
) -> None:
    _execute_primary("generate", project, page, config)


@app.command()
def quality(
    project: str, page: str, config: Path = typer.Option(Path("config.yaml"), "--config")
) -> None:
    _execute_primary("quality", project, page, config)


@app.command()
def continuity(
    project: str, page: str, config: Path = typer.Option(Path("config.yaml"), "--config")
) -> None:
    _execute_support("continuity", project, page, config)


@app.command()
def approve(
    project: str,
    page: str,
    approved_by: str = typer.Option(..., "--approved-by"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    _execute_primary("approve", project, page, config, {"approved_by": approved_by})


@app.command()
def run(
    project: str, page: str, config: Path = typer.Option(Path("config.yaml"), "--config")
) -> None:
    """Run legal automatic steps through QualityChecked; approval is always explicit."""
    logger = LOGGER

    def action() -> None:
        def execute(runtime: CliRuntime) -> None:
            logger.info("Workflow start: run %s/%s", project, page)
            repository = runtime.loader.repository
            if isinstance(repository, LocalFileRepository):
                composition = getattr(runtime, "localfile_external_generation", None)
                if composition is None:
                    result = _route_localfile_run(runtime.engine, repository, project, page)
                else:
                    result = _route_localfile_run(
                        runtime.engine,
                        repository,
                        project,
                        page,
                        logical_output_asset_quality_gate=composition.quality_gate,
                    )
                logger.info("Workflow end: run at %s", result.current_state.value)
                _emit(result)
                return
            context = runtime.loader.load(project, page)
            results = runtime.engine.run(context)
            final_context = results[-1].context if results else context
            runtime.loader.save(project, page, final_context)
            logger.info("Workflow end: run at %s", final_context.state.value)
            _emit(results[-1] if results else runtime.engine.status(final_context))

        _use_runtime(config, execute)

    _handle_error(logger, action)


@app.command()
def status(
    project: str, page: str, config: Path = typer.Option(Path("config.yaml"), "--config")
) -> None:
    """Show current state, steps, executable step, and workflow history."""
    logger = LOGGER

    _handle_error(
        logger,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(runtime.engine.status(runtime.loader.load(project, page))),
        ),
    )


@project_app.command("create")
def project_create(
    project_id: str = typer.Option(..., "--id"),
    title: str = typer.Option(..., "--title"),
    page_number: int = typer.Option(1, "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Create and persist a Project aggregate with its first Draft page."""
    logger = LOGGER

    def action() -> None:
        def execute(runtime: CliRuntime) -> None:
            logger.info("Project create: %s", project_id)
            _emit(runtime.coordinator.create_project(project_id, title, page_number))

        _use_runtime(config, execute, create_config=True)

    _handle_error(logger, action)


@project_app.command("open")
def project_open(
    project_id: str = typer.Argument(...),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Display the persisted Project aggregate."""
    logger = LOGGER

    def action() -> None:
        _use_runtime(config, lambda runtime: _emit(runtime.loader.open(project_id)))

    _handle_error(logger, action)


@project_app.command("list")
def project_list(config: Path = typer.Option(Path("config.yaml"), "--config")) -> None:
    """List persisted projects."""
    logger = LOGGER

    def action() -> None:
        _use_runtime(config, lambda runtime: _emit(runtime.loader.list()))

    _handle_error(logger, action)


@project_app.command("delete")
def project_delete(
    project_id: str = typer.Argument(...),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Delete one persisted Project aggregate."""
    logger = LOGGER

    def action() -> None:
        def execute(runtime: CliRuntime) -> None:
            runtime.loader.delete(project_id)
            _emit({"deleted": project_id})

        _use_runtime(config, execute)

    _handle_error(logger, action)


@project_app.command("export")
def project_export(
    project_id: str = typer.Argument(...),
    output: Path = typer.Option(..., "--output"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Export a Project as JSON or YAML based on the output suffix."""
    logger = LOGGER

    def action() -> None:
        def execute(runtime: CliRuntime) -> None:
            runtime.loader.export(project_id, output)
            _emit({"exported": project_id, "output": str(output)})

        _use_runtime(config, execute)

    _handle_error(logger, action)


@project_app.command("import")
def project_import(
    source: Path = typer.Option(..., "--source"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Import a Project document without overwriting an existing ID."""
    logger = LOGGER

    def action() -> None:
        _use_runtime(config, lambda runtime: _emit(runtime.loader.import_(source)))

    _handle_error(logger, action)


@project_app.command("run")
def project_run(
    project_id: str = typer.Argument(...),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Run exactly the next page in the project's current chapter through QualityChecked."""

    def action() -> None:
        def execute(runtime: CliRuntime) -> None:
            LOGGER.info("Project workflow start: %s", project_id)
            result = runtime.coordinator.run_project(project_id)
            LOGGER.info("Project workflow end: %s", project_id)
            _emit(result)

        _use_runtime(config, execute)

    _handle_error(LOGGER, action)


@project_app.command("resume")
def project_resume(
    project_id: str = typer.Argument(...),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Resume a Project workflow by scheduling its next eligible page."""

    def action() -> None:
        _use_runtime(config, lambda runtime: _emit(runtime.coordinator.resume_project(project_id)))

    _handle_error(LOGGER, action)


@project_app.command("status")
def project_status(
    project_id: str = typer.Argument(...),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Show project progress, current chapter, current page, and lifecycle history."""
    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(runtime.coordinator.project_status(project_id)),
        ),
    )


@chapter_app.command("run")
def chapter_run(
    project_id: str = typer.Argument(...),
    chapter_id: str = typer.Argument(...),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Run exactly the next page in one chapter through QualityChecked."""

    def action() -> None:
        _use_runtime(
            config,
            lambda runtime: _emit(runtime.coordinator.run_chapter(project_id, chapter_id)),
        )

    _handle_error(LOGGER, action)


@chapter_app.command("status")
def chapter_status(
    project_id: str = typer.Argument(...),
    chapter_id: str = typer.Argument(...),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Show ordered chapter pages, current page, review metadata, and history."""
    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(runtime.coordinator.chapter_status(project_id, chapter_id)),
        ),
    )


@mcp_app.command("serve")
def mcp_serve(config: Path = typer.Option(Path("config.yaml"), "--config")) -> None:
    """Serve MCP JSON-RPC through local standard input/output only."""
    _handle_error(
        LOGGER,
        lambda: _use_runtime(config, lambda runtime: _mcp_server(runtime, config).serve_stdio()),
    )


@mcp_app.command("tools")
def mcp_tools(config: Path = typer.Option(Path("config.yaml"), "--config")) -> None:
    """List locally available MCP tools and their JSON input schemas."""
    _handle_error(
        LOGGER,
        lambda: _use_runtime(config, lambda runtime: _emit(_mcp_server(runtime, config).tools())),
    )


@mcp_app.command("resources")
def mcp_resources(config: Path = typer.Option(Path("config.yaml"), "--config")) -> None:
    """List read-only local MCP resources."""
    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config, lambda runtime: _emit(_mcp_server(runtime, config).resources())
        ),
    )


@mcp_app.command("prompts")
def mcp_prompts(config: Path = typer.Option(Path("config.yaml"), "--config")) -> None:
    """List Markdown-backed MCP prompts."""
    _handle_error(
        LOGGER,
        lambda: _use_runtime(config, lambda runtime: _emit(_mcp_server(runtime, config).prompts())),
    )


@batch_app.command("run")
def batch_run(
    project_id: str = typer.Argument(...),
    batch_id: str | None = typer.Option(None, "--id"),
    chapter: list[str] = typer.Option([], "--chapter"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Create and sequentially run a persisted Batch through existing page workflows."""

    def action() -> None:
        _use_runtime(
            config,
            lambda runtime: _emit(
                runtime.batch.run(project_id, batch_id=batch_id, chapter_ids=chapter or None)
            ),
        )

    _handle_error(LOGGER, action)


@batch_app.command("resume")
def batch_resume(
    project_id: str = typer.Argument(...),
    batch_id: str = typer.Argument(...),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Resume only pending pages from a persisted Batch."""
    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(runtime.batch.resume(project_id, batch_id)),
        ),
    )


@batch_app.command("retry")
def batch_retry(
    project_id: str = typer.Argument(...),
    batch_id: str = typer.Argument(...),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Retry failed pages only; completed pages remain untouched."""
    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(runtime.batch.retry(project_id, batch_id)),
        ),
    )


@batch_app.command("status")
def batch_status(
    project_id: str = typer.Argument(...),
    batch_id: str = typer.Argument(...),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Show persisted Queue, progress, logs, and execution policy outcome."""
    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(runtime.batch.status(project_id, batch_id)),
        ),
    )


@plugin_app.command("list")
def plugin_list(config: Path = typer.Option(Path("config.yaml"), "--config")) -> None:
    """List discovered local plugins without importing their code."""

    def action() -> None:
        statuses = _plugin_manager(config).statuses()
        _emit([status.as_dict() for status in statuses])

    _handle_error(LOGGER, action)


@plugin_app.command("info")
def plugin_info(
    name: str,
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Show one plugin manifest's metadata."""
    _handle_error(LOGGER, lambda: _emit(_plugin_manager(config).info(name).as_dict()))


@plugin_app.command("install")
def plugin_install(
    source: Path = typer.Option(..., "--source"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Install a plugin from a local directory; remote sources are unsupported."""
    _handle_error(
        LOGGER,
        lambda: _emit(_plugin_manager(config, create_config=True).install(source).as_dict()),
    )


@plugin_app.command("enable")
def plugin_enable(
    name: str,
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Enable a plugin for the next runtime startup."""
    _handle_error(
        LOGGER,
        lambda: _emit(_plugin_manager(config).enable(name).model_dump(mode="json")),
    )


@plugin_app.command("disable")
def plugin_disable(
    name: str,
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Disable a plugin for the next runtime startup."""
    _handle_error(
        LOGGER,
        lambda: _emit(_plugin_manager(config).disable(name).model_dump(mode="json")),
    )


@plugin_app.command("remove")
def plugin_remove(
    name: str,
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Remove one locally installed plugin by exact manifest name."""

    def action() -> None:
        _plugin_manager(config).remove(name)
        _emit({"removed": name})

    _handle_error(LOGGER, action)


@planning_app.command("preview")
def planning_preview(
    project: str = typer.Argument(...),
    page: str = typer.Argument(...),
    capability: list[str] = typer.Option([], "--capability"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Preview exactly one persisted page without running a workflow step."""

    def action() -> None:
        def execute(runtime: CliRuntime) -> None:
            context = runtime.loader.load(project, page)
            _emit(
                _planning_service(runtime).summary(
                    context,
                    required_capabilities=capability,
                    configuration=runtime.config.model_dump(mode="json"),
                )
            )

        _use_runtime(config, execute)

    _handle_error(LOGGER, action)


@planning_app.command("provider")
def planning_provider(
    capability: list[str] = typer.Option([], "--capability"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Preview metadata-only Provider selection; no Provider request is issued."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(_planning_service(runtime).provider_preview(capability)),
        ),
    )


@planning_app.command("configuration")
def planning_configuration(config: Path = typer.Option(Path("config.yaml"), "--config")) -> None:
    """Preview only the configured keys, never secret values."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _planning_service(runtime).configuration_preview(
                    runtime.config.model_dump(mode="json")
                )
            ),
        ),
    )


@planning_app.command("architecture")
def planning_architecture(config: Path = typer.Option(Path("config.yaml"), "--config")) -> None:
    """Show the planning boundary guarantees for integration review."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config, lambda runtime: _emit(_planning_service(runtime).architecture_preview())
        ),
    )


@director_app.command("preview")
def director_preview(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Preview an advisory Director plan without invoking a workflow step."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _director_service(runtime).director_plan(runtime.loader.load(project, page))
            ),
        ),
    )


@director_app.command("knowledge")
def director_knowledge(config: Path = typer.Option(Path("config.yaml"), "--config")) -> None:
    """Summarize repository-derived knowledge without writing to the repository."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config, lambda runtime: _emit(_director_service(runtime).knowledge_report())
        ),
    )


@director_app.command("workflow")
def director_workflow(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Visualize remaining one-page workflow dependencies without scheduling work."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _director_service(runtime).orchestration(runtime.loader.load(project, page))
            ),
        ),
    )


@director_app.command("strategy")
def director_strategy(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Return a read-only execution-strategy preview for one Page."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _director_service(runtime)
                .director_plan(runtime.loader.load(project, page))
                .strategy
            ),
        ),
    )


@director_app.command("analysis")
def director_analysis(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Compare advisory Director alternatives and workflow optimization evidence."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                {
                    "director": _intelligence_service(runtime).director_analysis(
                        runtime.loader.load(project, page)
                    ),
                    "workflow": _intelligence_service(runtime).workflow_optimization(
                        runtime.loader.load(project, page)
                    ),
                }
            ),
        ),
    )


@director_app.command("dashboard")
def director_dashboard(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render a read-only Knowledge, Director, and optimization dashboard DTO."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _intelligence_service(runtime).dashboard(runtime.loader.load(project, page))
            ),
        ),
    )


@director_app.command("reliability")
def director_reliability(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Validate one advisory Director plan without executing a workflow command."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _director_reliability_service(runtime).director_reliability(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("governance")
def director_governance(config: Path = typer.Option(Path("config.yaml"), "--config")) -> None:
    """Return read-only Knowledge policy, integrity, lifecycle, quality, and risk evidence."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(_director_reliability_service(runtime).knowledge_governance()),
        ),
    )


@director_app.command("readiness")
def director_readiness(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Return an enterprise AI checklist; it cannot deploy, resume, or execute work."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _director_reliability_service(runtime).enterprise_ai_readiness(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("diagnostics")
def director_diagnostics(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render Director, Knowledge, planning, workflow, and architecture diagnostics."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _director_reliability_service(runtime).diagnostics(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("executive")
def director_executive(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render a transport-neutral Director, Knowledge, Workflow, Enterprise, and Release dashboard."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _director_reliability_service(runtime).dashboard(runtime.loader.load(project, page))
            ),
        ),
    )


@director_app.command("platform")
def director_platform(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render a v3 Director session DTO without executing a workflow command."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _director_platform_service(runtime).director_platform(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("creative")
def director_creative(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render a v3 creative planning DTO without image generation or state change."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _director_platform_service(runtime).creative_dashboard(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("foundation")
def director_foundation(config: Path = typer.Option(Path("config.yaml"), "--config")) -> None:
    """Render a repository-derived v3 Knowledge Foundation DTO without writes."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config, lambda runtime: _emit(_director_platform_service(runtime).knowledge_dashboard())
        ),
    )


@director_app.command("intelligence")
def director_intelligence(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render a v3 Workflow Intelligence DTO without changing the workflow."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _director_platform_service(runtime).workflow_dashboard(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("summary")
def director_summary(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render a compact v3 planning summary for one Page without execution."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _director_platform_service(runtime).planning_summary(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("collaboration")
def director_collaboration(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render a proposed multi-agent collaboration plan without running an Agent."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _collaboration_service(runtime).agent_dashboard(runtime.loader.load(project, page))
            ),
        ),
    )


@director_app.command("creative-knowledge")
def director_creative_knowledge(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render repository-derived creative knowledge without writes or hidden values."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _collaboration_service(runtime).creative_knowledge_dashboard(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("creative-intelligence")
def director_creative_intelligence(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render advisory creative alternatives, risks, and recommendations only."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _collaboration_service(runtime).director_intelligence_dashboard(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("review-pipeline")
def director_review_pipeline(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render diagnostic story, storyboard, consistency, and quality review evidence."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _collaboration_service(runtime).review_pipeline_dashboard(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("reliability-v3")
def director_reliability_v3(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3 Director reliability validation without executing workflow work."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v3_readiness_service(runtime).director_executive(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("creative-governance")
def director_creative_governance(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3 Creative governance evidence without changing a creative artifact."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v3_readiness_service(runtime).creative_executive(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("knowledge-integrity")
def director_knowledge_integrity(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3 read-only Knowledge integrity evidence for one page context."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v3_readiness_service(runtime).knowledge_executive(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("production-readiness")
def director_production_readiness(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render a v3 deployment-readiness checklist; no deployment is started."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v3_readiness_service(runtime).production_executive(
                    runtime.loader.load(project, page), runtime.config.model_dump(mode="json")
                )
            ),
        ),
    )


@director_app.command("release-dashboard")
def director_release_dashboard(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render a v3 release-readiness dashboard without authorizing a release."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v3_readiness_service(runtime).release_dashboard(
                    runtime.loader.load(project, page), runtime.config.model_dump(mode="json")
                )
            ),
        ),
    )


@director_app.command("collaboration-foundation")
def director_collaboration_foundation(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.1 human collaboration evidence without Agent execution or approval."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v31_foundation_service(runtime).collaboration_dashboard(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("knowledge-evolution")
def director_knowledge_evolution(
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render read-only v3.1 Knowledge history, snapshot, diff, and timeline evidence."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(_v31_foundation_service(runtime).knowledge_evolution_dashboard()),
        ),
    )


@director_app.command("operations-foundation")
def director_operations_foundation(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.1 local operations metrics without automation or runtime control."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v31_foundation_service(runtime).operations_dashboard(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("developer-productivity")
def director_developer_productivity(
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.1 project, planning, validation, and workspace template descriptors."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v31_foundation_service(runtime).developer_productivity_dashboard()
            ),
        ),
    )


@director_app.command("project-metrics")
def director_project_metrics(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.1 aggregate Project metrics without running multiple pages."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v31_foundation_service(runtime)
                .operations_dashboard(runtime.loader.load(project, page))
                .report.project
            ),
        ),
    )


@director_app.command("creative-review")
def director_creative_review(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render advisory creative review evidence without review execution or approval."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v31_insights_service(runtime).creative_review_dashboard(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("knowledge-analytics")
def director_knowledge_analytics(
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render redacted Repository-port Knowledge analytics without writes."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(_v31_insights_service(runtime).knowledge_analytics_dashboard()),
        ),
    )


@director_app.command("operations-intelligence")
def director_operations_intelligence(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render operations observations without modifying runtime operations."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v31_insights_service(runtime).operations_intelligence_dashboard(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("developer-experience")
def director_developer_experience(
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render template and configuration-shape guidance without applying changes."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v31_insights_service(runtime).developer_experience_dashboard(
                    runtime.config.model_dump(mode="json")
                )
            ),
        ),
    )


@director_app.command("workflow-efficiency")
def director_workflow_efficiency(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render one-Page efficiency observations without dispatching a workflow step."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v31_insights_service(runtime)
                .operations_intelligence_dashboard(runtime.loader.load(project, page))
                .report.workflow_efficiency
            ),
        ),
    )


@director_app.command("creative-governance-v31")
def director_creative_governance_v31(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.1 creative-governance evidence without approval or remediation."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v31_assurance_service(runtime).creative_governance_dashboard(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("knowledge-reliability")
def director_knowledge_reliability(
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.1 Knowledge reliability evidence without persistence changes."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v31_assurance_service(runtime).knowledge_reliability_dashboard()
            ),
        ),
    )


@director_app.command("operational-readiness-v31")
def director_operational_readiness_v31(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render readiness evidence without deployment, configuration, or runtime changes."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v31_assurance_service(runtime).operational_readiness_dashboard(
                    runtime.loader.load(project, page), runtime.config.model_dump(mode="json")
                )
            ),
        ),
    )


@director_app.command("release-quality")
def director_release_quality(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render release-quality diagnostics without authorizing a release."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v31_assurance_service(runtime).release_quality_dashboard(
                    runtime.loader.load(project, page), runtime.config.model_dump(mode="json")
                )
            ),
        ),
    )


@director_app.command("compatibility-validation")
def director_compatibility_validation(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render compatibility evidence without changing any public interface."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v31_assurance_service(runtime)
                .release_quality_dashboard(
                    runtime.loader.load(project, page), runtime.config.model_dump(mode="json")
                )
                .report.compatibility
            ),
        ),
    )


@director_app.command("creative-studio")
def director_creative_studio(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render a v3.2 Studio workspace DTO without workflow execution."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v32_foundation_service(runtime).creative_studio_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("asset-intelligence")
def director_asset_intelligence(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render redacted v3.2 Asset intelligence without repository mutation."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v32_foundation_service(runtime).asset_intelligence_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("workflow-profiles")
def director_workflow_profiles(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.2 StateMachine profiles without performing a transition."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v32_foundation_service(runtime).workflow_profile_dashboard(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("production-analytics")
def director_production_analytics(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.2 Production analytics without automation or approval."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v32_foundation_service(runtime).production_analytics_dashboard(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("workspace-dashboard")
def director_workspace_dashboard(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render the v3.2 Studio dashboard only; no layout is persisted."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v32_foundation_service(runtime).creative_studio_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("creative-workspace")
def director_creative_workspace(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.2 Workspace analysis without creating tasks or approval."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v32_insights_service(runtime).creative_workspace_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("asset-analytics")
def director_asset_analytics(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render redacted v3.2 Asset Analytics without index mutation."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v32_insights_service(runtime).asset_analytics_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("workflow-intelligence-v32")
def director_workflow_intelligence_v32(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.2 Workflow Intelligence without workflow execution."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v32_insights_service(runtime).workflow_intelligence_dashboard(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("production-insights")
def director_production_insights(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.2 Production Insights without forecasting or automation."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v32_insights_service(runtime).production_insights_dashboard(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("pipeline-analysis")
def director_pipeline_analysis(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render a v3.2 Pipeline bottleneck DTO without applying a profile."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v32_insights_service(runtime)
                .workflow_intelligence_dashboard(runtime.loader.load(project, page))
                .report.bottleneck
            ),
        ),
    )


@director_app.command("creative-reliability")
def director_creative_reliability(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.2 Creative Reliability evidence without workflow execution."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v32_assurance_service(runtime).creative_reliability_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("asset-governance")
def director_asset_governance(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.2 Asset Governance diagnostics without repository mutation."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v32_assurance_service(runtime).asset_governance_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("operational-intelligence-v32")
def director_operational_intelligence_v32(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.2 Operational Intelligence without operational changes."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v32_assurance_service(runtime).operational_intelligence_dashboard(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("release-readiness-v32")
def director_release_readiness_v32(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.2 Release Readiness evidence without authorizing a release."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v32_assurance_service(runtime).release_readiness_dashboard(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("compatibility-validation-v32")
def director_compatibility_validation_v32(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.2 compatibility evidence without changing any interface."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v32_assurance_service(runtime)
                .release_readiness_dashboard(runtime.loader.load(project, page))
                .report.compatibility
            ),
        ),
    )


@director_app.command("production-pipeline-v33")
def director_production_pipeline_v33(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.3 Production Pipeline evidence without execution or publishing."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v33_foundation_service(runtime).production_pipeline_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("quality-intelligence-v33")
def director_quality_intelligence_v33(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.3 Quality Intelligence without scoring or approval authority."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v33_foundation_service(runtime).quality_intelligence_dashboard(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("asset-lifecycle-v33")
def director_asset_lifecycle_v33(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.3 Asset Lifecycle evidence without repository mutation."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v33_foundation_service(runtime).asset_lifecycle_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("project-intelligence-v33")
def director_project_intelligence_v33(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.3 Project Intelligence without scheduling or allocation."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v33_foundation_service(runtime).project_intelligence_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("production-intelligence-v33")
def director_production_intelligence_v33(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.3 Production Intelligence without workflow modification."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v33_insights_service(runtime).production_intelligence_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("quality-analytics-v33")
def director_quality_analytics_v33(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.3 Quality Analytics without scoring or approval authority."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v33_insights_service(runtime).quality_analytics_dashboard(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("asset-intelligence-v33")
def director_asset_intelligence_v33(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.3 Asset Intelligence without repository mutation."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v33_insights_service(runtime).asset_intelligence_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("project-operations-v33")
def director_project_operations_v33(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.3 Project Operations without scheduling or allocation."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v33_insights_service(runtime).project_operations_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("production-governance-v33")
def director_production_governance_v33(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.3 Production Governance without pipeline changes or execution."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v33_governance_service(runtime).production_governance_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("quality-governance-v33")
def director_quality_governance_v33(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.3 Quality Governance without scoring or approval authority."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v33_governance_service(runtime).quality_governance_dashboard(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("asset-governance-v33")
def director_asset_governance_v33(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.3 Asset Governance without retention or repository mutation."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v33_governance_service(runtime).asset_governance_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("project-governance-v33")
def director_project_governance_v33(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.3 Project Governance without scheduling or allocation."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v33_governance_service(runtime).project_governance_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("knowledge-platform-v34")
def director_knowledge_platform_v34(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.4 Knowledge Platform evidence without repository mutation."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v34_foundation_service(runtime).knowledge_platform_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("production-operations-v34")
def director_production_operations_v34(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.4 Production Operations without monitoring or deployment."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v34_foundation_service(runtime).production_operations_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("organization-intelligence-v34")
def director_organization_intelligence_v34(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.4 Organization Intelligence without personnel action."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v34_foundation_service(runtime).organization_intelligence_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("release-intelligence-v34")
def director_release_intelligence_v34(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.4 Release Intelligence without publication authority."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v34_foundation_service(runtime).release_intelligence_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("knowledge-intelligence-v34")
def director_knowledge_intelligence_v34(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.4 Knowledge Intelligence without repository mutation."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v34_insights_service(runtime).knowledge_intelligence_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("production-optimization-v34")
def director_production_optimization_v34(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.4 Production Optimization without workflow modification."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v34_insights_service(runtime).production_optimization_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("organization-analytics-v34")
def director_organization_analytics_v34(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.4 Organization Analytics without personnel action."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v34_insights_service(runtime).organization_analytics_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("release-analytics-v34")
def director_release_analytics_v34(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.4 Release Analytics without release authority."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v34_insights_service(runtime).release_analytics_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("knowledge-governance-v34")
def director_knowledge_governance_v34(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.4 Knowledge Governance without repository mutation."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v34_governance_service(runtime).knowledge_governance_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("production-governance-v34")
def director_production_governance_v34(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.4 Production Governance without pipeline modification."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v34_governance_service(runtime).production_governance_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("organization-governance-v34")
def director_organization_governance_v34(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.4 Organization Governance without personnel action."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v34_governance_service(runtime).organization_governance_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("release-governance-v34")
def director_release_governance_v34(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.4 Release Governance without release authority."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v34_governance_service(runtime).release_governance_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("knowledge-graph-v35")
def director_knowledge_graph_v35(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.5 Knowledge Graph evidence without graph persistence."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v35_foundation_service(runtime).knowledge_graph_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("creative-intelligence-v35")
def director_creative_intelligence_v35(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.5 Creative Intelligence without generation or approval."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v35_foundation_service(runtime).creative_intelligence_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("production-intelligence-v35")
def director_production_intelligence_v35(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.5 Production Intelligence without scheduling or deployment."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v35_foundation_service(runtime).production_intelligence_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("platform-analytics-v35")
def director_platform_analytics_v35(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.5 Platform Analytics without collection or external action."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v35_foundation_service(runtime).platform_analytics_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("knowledge-insights-v35")
def director_knowledge_insights_v35(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.5 Knowledge Analytics without graph mutation."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v35_insights_service(runtime).knowledge_insights_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("creative-analytics-v35")
def director_creative_analytics_v35(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.5 Creative Analytics without generation or approval."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v35_insights_service(runtime).creative_analytics_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("production-analytics-v35")
def director_production_analytics_v35(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.5 Production Analytics without scheduling or deployment."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v35_insights_service(runtime).production_analytics_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("executive-analytics-v35")
def director_executive_analytics_v35(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.5 Executive Analytics without collection or external action."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v35_insights_service(runtime).executive_analytics_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("knowledge-governance-v35")
def director_knowledge_governance_v35(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.5 Knowledge Governance without policy enforcement."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v35_governance_service(runtime).knowledge_governance_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("creative-governance-v35")
def director_creative_governance_v35(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.5 Creative Governance without a creative or approval action."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v35_governance_service(runtime).creative_governance_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("production-governance-v35")
def director_production_governance_v35(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.5 Production Governance without workflow or deployment action."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v35_governance_service(runtime).production_governance_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@director_app.command("platform-governance-v35")
def director_platform_governance_v35(
    project: str = typer.Option(..., "--project"),
    page: str = typer.Option("1", "--page"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render v3.5 Platform Governance without monitoring or external action."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _v35_governance_service(runtime).platform_governance_dashboard(
                    project, runtime.loader.load(project, page)
                )
            ),
        ),
    )


@analytics_app.command("workflow")
def analytics_workflow(
    project: str = typer.Argument(...),
    page: str = typer.Argument(...),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Analyze one persisted Page without running its next workflow command."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _analytics_service(runtime).workflow_analysis(runtime.loader.load(project, page))
            ),
        ),
    )


@analytics_app.command("providers")
def analytics_providers(
    capability: list[str] = typer.Option([], "--capability"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Compare local Provider metadata and construction health without a request."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(_analytics_service(runtime).provider_comparison(capability)),
        ),
    )


@analytics_app.command("enterprise")
def analytics_enterprise(
    project: str = typer.Argument(...),
    page: str = typer.Argument(...),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render configuration, workflow, Provider, Backend, and Repository audits."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _analytics_service(runtime).enterprise_diagnostics(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@analytics_app.command("operations")
def analytics_operations(
    project: str = typer.Argument(...),
    page: str = typer.Argument(...),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Show bounded operational trends without starting collection or automation."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _analytics_service(runtime).operational_analytics(
                    runtime.loader.load(project, page)
                )
            ),
        ),
    )


@analytics_app.command("executive")
def analytics_executive(
    project: str = typer.Argument(...),
    page: str = typer.Argument(...),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render a compact, non-executing workflow, Provider, and operations report."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _analytics_service(runtime).executive_report(runtime.loader.load(project, page))
            ),
        ),
    )


@assurance_app.command("workflow")
def assurance_workflow(
    project: str = typer.Argument(...),
    page: str = typer.Argument(...),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Validate one persisted Page's integrity, risks, and advisory readiness."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _assurance_service(runtime).workflow_reliability(runtime.loader.load(project, page))
            ),
        ),
    )


@assurance_app.command("providers")
def assurance_providers(config: Path = typer.Option(Path("config.yaml"), "--config")) -> None:
    """Review Provider policy, capability, lifecycle, compatibility, and risk evidence."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config, lambda runtime: _emit(_assurance_service(runtime).provider_governance())
        ),
    )


@assurance_app.command("enterprise")
def assurance_enterprise(
    project: str = typer.Argument(...),
    page: str = typer.Argument(...),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render deployment, operations, maintenance, configuration, and recovery readiness."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _assurance_service(runtime).enterprise_readiness(runtime.loader.load(project, page))
            ),
        ),
    )


@assurance_app.command("diagnostics")
def assurance_diagnostics(
    project: str = typer.Argument(...),
    page: str = typer.Argument(...),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render planning, dependency, execution, architecture, and workflow-health evidence."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _assurance_service(runtime).workflow_diagnostics(runtime.loader.load(project, page))
            ),
        ),
    )


@assurance_app.command("dashboard")
def assurance_dashboard(
    project: str = typer.Argument(...),
    page: str = typer.Argument(...),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Render dashboard DTOs without presenting UI or triggering a release."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(
                _assurance_service(runtime).dashboard(runtime.loader.load(project, page))
            ),
        ),
    )


@diagnostics_app.command("run")
def diagnostics_run(config: Path = typer.Option(Path("config.yaml"), "--config")) -> None:
    """Run safe system diagnostics and emit a transport-neutral DTO."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(config, lambda runtime: _emit(_runtime_report(runtime, config))),
    )


@diagnostics_app.command("report")
def diagnostics_report(config: Path = typer.Option(Path("config.yaml"), "--config")) -> None:
    """Emit the same safe diagnostic report for scripts and release checks."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(config, lambda runtime: _emit(_runtime_report(runtime, config))),
    )


@diagnostics_app.command("export")
def diagnostics_export(
    output: Path = typer.Option(..., "--output"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Export a safe diagnostic report as JSON or Markdown based on its suffix."""

    def action() -> None:
        def execute(runtime: CliRuntime) -> None:
            report = _runtime_report(runtime, config)
            suffix = output.suffix.lower()
            if suffix == ".md":
                content = report.to_markdown()
            elif suffix == ".json":
                content = report.to_json()
            else:
                raise ValueError("Diagnostic output must use .json or .md")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(content + "\n", encoding="utf-8")
            _emit({"exported": str(output)})

        _use_runtime(config, execute)

    _handle_error(LOGGER, action)


@health_app.command("check")
def health_check(config: Path = typer.Option(Path("config.yaml"), "--config")) -> None:
    """Run isolated health probes for configured runtime boundaries."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(config, lambda runtime: _emit(_health_dashboard(runtime, config))),
    )


@health_app.command("summary")
def health_summary(config: Path = typer.Option(Path("config.yaml"), "--config")) -> None:
    """Return provider, backend, repository, workflow, and configuration health."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config, lambda runtime: _emit(_runtime_health(runtime, config).report())
        ),
    )


@repository_app.command("check")
def repository_check(
    project_id: str | None = typer.Option(None, "--project"),
    config: Path = typer.Option(Path("config.yaml"), "--config"),
) -> None:
    """Validate persisted project, history, metadata, and workflow snapshot integrity."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(RepositorySelfCheck(runtime.loader.repository).check(project_id)),
        ),
    )


@provider_app.command("check")
def provider_check(config: Path = typer.Option(Path("config.yaml"), "--config")) -> None:
    """Check locally constructible LLM providers without issuing a model request."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(_runtime_health(runtime, config).report().provider),
        ),
    )


@backend_app.command("check")
def backend_check(config: Path = typer.Option(Path("config.yaml"), "--config")) -> None:
    """Check locally constructible image backends without generating an image."""

    _handle_error(
        LOGGER,
        lambda: _use_runtime(
            config,
            lambda runtime: _emit(_runtime_health(runtime, config).report().backend),
        ),
    )


@app.command("system-summary")
def system_summary(config: Path = typer.Option(Path("config.yaml"), "--config")) -> None:
    """Emit the system and health portions of the release diagnostic DTOs."""

    def action() -> None:
        def execute(runtime: CliRuntime) -> None:
            report = _runtime_report(runtime, config)
            health = _health_dashboard(runtime, config)
            _emit({"system": report.system, "health": health.model_dump(mode="json")})

        _use_runtime(config, execute)

    _handle_error(LOGGER, action)
