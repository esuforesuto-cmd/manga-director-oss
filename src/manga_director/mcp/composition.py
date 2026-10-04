"""Dependency-injection composition for MCP, separate from transport and domain code."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from threading import Lock
from typing import Any

from manga_director.cli.config import AppConfig
from manga_director.mcp.application import MangaApplicationService
from manga_director.mcp.prompts import McpPromptLoader
from manga_director.mcp.registry import default_tool_registry
from manga_director.mcp.resources import McpResourceProvider
from manga_director.mcp.server import McpServer
from manga_director.repositories.local_file import LocalFileRepository
from manga_director.repositories.project_loader import ProjectLoader
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext
from manga_director.workflow.coordinator import WorkflowCoordinator
from manga_director.workflow.durable_execution import LogicalOutputAssetQualityGatePort
from manga_director.workflow.engine import WorkflowEngine
from manga_director.workflow.localfile_external_generated_application import (
    build_localfile_quality_ledger_gate,
)


class _LazyLocalFileQualityGate:
    """Build the LocalFile quality Ledger only when an execution invokes it."""

    def __init__(self, repository: LocalFileRepository) -> None:
        self._repository = repository
        self._delegate: LogicalOutputAssetQualityGatePort | None = None
        self._lock = Lock()

    def require_applied(self, context: WorkflowContext) -> str | None:
        return self._resolve().require_applied(context)

    def _resolve(self) -> LogicalOutputAssetQualityGatePort:
        if self._delegate is None:
            with self._lock:
                if self._delegate is None:
                    self._delegate = build_localfile_quality_ledger_gate(self._repository)
        return self._delegate


def build_mcp_server(
    *,
    workflow_engine: WorkflowEngine,
    workflow_coordinator: WorkflowCoordinator,
    project_loader: ProjectLoader,
    repository: ProjectRepository,
    prompt_directory: Path | None = None,
    configuration: AppConfig | None = None,
    diagnostics_provider: Callable[[], Any] | None = None,
    health_provider: Callable[[], Any] | None = None,
    provider_health_provider: Callable[[], Any] | None = None,
    backend_health_provider: Callable[[], Any] | None = None,
    repository_check_provider: Callable[[], Any] | None = None,
    planning_provider: Callable[[], Any] | None = None,
    provider_selection_provider: Callable[[], Any] | None = None,
    analytics_provider: Callable[[], Any] | None = None,
    enterprise_provider: Callable[[], Any] | None = None,
    executive_provider: Callable[[], Any] | None = None,
    assurance_provider: Callable[[], Any] | None = None,
    provider_governance_provider: Callable[[], Any] | None = None,
    dashboard_provider: Callable[[], Any] | None = None,
    director_provider: Callable[[], Any] | None = None,
    knowledge_provider: Callable[[], Any] | None = None,
    orchestration_provider: Callable[[], Any] | None = None,
    director_reliability_provider: Callable[[], Any] | None = None,
    knowledge_governance_provider: Callable[[], Any] | None = None,
    enterprise_ai_readiness_provider: Callable[[], Any] | None = None,
    ai_workflow_diagnostics_provider: Callable[[], Any] | None = None,
    director_dashboard_provider: Callable[[], Any] | None = None,
    director_platform_provider: Callable[[], Any] | None = None,
    creative_planning_provider: Callable[[], Any] | None = None,
    knowledge_foundation_provider: Callable[[], Any] | None = None,
    workflow_intelligence_provider: Callable[[], Any] | None = None,
    planning_summary_provider: Callable[[], Any] | None = None,
    multi_agent_provider: Callable[[], Any] | None = None,
    creative_knowledge_provider: Callable[[], Any] | None = None,
    director_intelligence_provider: Callable[[], Any] | None = None,
    review_pipeline_provider: Callable[[], Any] | None = None,
    knowledge_relationship_provider: Callable[[], Any] | None = None,
    director_reliability_v3_provider: Callable[[], Any] | None = None,
    creative_governance_provider: Callable[[], Any] | None = None,
    knowledge_integrity_provider: Callable[[], Any] | None = None,
    production_readiness_provider: Callable[[], Any] | None = None,
    release_readiness_provider: Callable[[], Any] | None = None,
    collaboration_foundation_provider: Callable[[], Any] | None = None,
    knowledge_evolution_provider: Callable[[], Any] | None = None,
    operations_foundation_provider: Callable[[], Any] | None = None,
    developer_productivity_provider: Callable[[], Any] | None = None,
    project_metrics_provider: Callable[[], Any] | None = None,
    creative_review_provider: Callable[[], Any] | None = None,
    knowledge_analytics_provider: Callable[[], Any] | None = None,
    operations_intelligence_provider: Callable[[], Any] | None = None,
    developer_experience_provider: Callable[[], Any] | None = None,
    workflow_efficiency_provider: Callable[[], Any] | None = None,
    creative_governance_v31_provider: Callable[[], Any] | None = None,
    knowledge_reliability_provider: Callable[[], Any] | None = None,
    operational_readiness_v31_provider: Callable[[], Any] | None = None,
    release_quality_provider: Callable[[], Any] | None = None,
    compatibility_validation_provider: Callable[[], Any] | None = None,
    creative_studio_v32_provider: Callable[[], Any] | None = None,
    asset_intelligence_v32_provider: Callable[[], Any] | None = None,
    workflow_profiles_v32_provider: Callable[[], Any] | None = None,
    production_analytics_v32_provider: Callable[[], Any] | None = None,
    workspace_dashboard_v32_provider: Callable[[], Any] | None = None,
    creative_workspace_v32_provider: Callable[[], Any] | None = None,
    asset_analytics_v32_provider: Callable[[], Any] | None = None,
    workflow_intelligence_v32_provider: Callable[[], Any] | None = None,
    production_insights_v32_provider: Callable[[], Any] | None = None,
    pipeline_analysis_v32_provider: Callable[[], Any] | None = None,
    creative_reliability_v32_provider: Callable[[], Any] | None = None,
    asset_governance_v32_provider: Callable[[], Any] | None = None,
    operational_intelligence_v32_provider: Callable[[], Any] | None = None,
    release_readiness_v32_provider: Callable[[], Any] | None = None,
    compatibility_validation_v32_provider: Callable[[], Any] | None = None,
    production_pipeline_v33_provider: Callable[[], Any] | None = None,
    quality_intelligence_v33_provider: Callable[[], Any] | None = None,
    asset_lifecycle_v33_provider: Callable[[], Any] | None = None,
    project_intelligence_v33_provider: Callable[[], Any] | None = None,
    production_intelligence_v33_provider: Callable[[], Any] | None = None,
    quality_analytics_v33_provider: Callable[[], Any] | None = None,
    asset_intelligence_v33_provider: Callable[[], Any] | None = None,
    project_operations_v33_provider: Callable[[], Any] | None = None,
    production_governance_v33_provider: Callable[[], Any] | None = None,
    quality_governance_v33_provider: Callable[[], Any] | None = None,
    asset_governance_v33_provider: Callable[[], Any] | None = None,
    project_governance_v33_provider: Callable[[], Any] | None = None,
    knowledge_platform_v34_provider: Callable[[], Any] | None = None,
    production_operations_v34_provider: Callable[[], Any] | None = None,
    organization_intelligence_v34_provider: Callable[[], Any] | None = None,
    release_intelligence_v34_provider: Callable[[], Any] | None = None,
    knowledge_intelligence_v34_provider: Callable[[], Any] | None = None,
    production_optimization_v34_provider: Callable[[], Any] | None = None,
    organization_analytics_v34_provider: Callable[[], Any] | None = None,
    release_analytics_v34_provider: Callable[[], Any] | None = None,
    knowledge_governance_v34_provider: Callable[[], Any] | None = None,
    production_governance_v34_provider: Callable[[], Any] | None = None,
    organization_governance_v34_provider: Callable[[], Any] | None = None,
    release_governance_v34_provider: Callable[[], Any] | None = None,
    knowledge_graph_v35_provider: Callable[[], Any] | None = None,
    creative_intelligence_v35_provider: Callable[[], Any] | None = None,
    production_intelligence_v35_provider: Callable[[], Any] | None = None,
    platform_analytics_v35_provider: Callable[[], Any] | None = None,
    knowledge_insights_v35_provider: Callable[[], Any] | None = None,
    creative_analytics_v35_provider: Callable[[], Any] | None = None,
    production_analytics_v35_provider: Callable[[], Any] | None = None,
    executive_analytics_v35_provider: Callable[[], Any] | None = None,
    knowledge_governance_v35_provider: Callable[[], Any] | None = None,
    creative_governance_v35_provider: Callable[[], Any] | None = None,
    production_governance_v35_provider: Callable[[], Any] | None = None,
    platform_governance_v35_provider: Callable[[], Any] | None = None,
) -> McpServer:
    """Build an MCP Server from injected abstractions, never concrete adapters."""
    configured_prompt_directory = prompt_directory
    if configured_prompt_directory is None and configuration is not None:
        configured_prompt_directory = configuration.prompt_directory
    localfile_quality_gate = (
        _LazyLocalFileQualityGate(repository)
        if isinstance(repository, LocalFileRepository)
        else None
    )
    service = MangaApplicationService(
        workflow_engine,
        workflow_coordinator,
        project_loader,
        repository,
        localfile_quality_gate=localfile_quality_gate,
    )
    return McpServer(
        default_tool_registry(
            service,
            diagnostics_provider=diagnostics_provider,
            health_provider=health_provider,
            provider_health_provider=provider_health_provider,
            backend_health_provider=backend_health_provider,
            repository_check_provider=repository_check_provider,
            planning_provider=planning_provider,
            provider_selection_provider=provider_selection_provider,
            analytics_provider=analytics_provider,
            enterprise_provider=enterprise_provider,
            executive_provider=executive_provider,
            assurance_provider=assurance_provider,
            provider_governance_provider=provider_governance_provider,
            dashboard_provider=dashboard_provider,
            director_provider=director_provider,
            knowledge_provider=knowledge_provider,
            orchestration_provider=orchestration_provider,
            director_reliability_provider=director_reliability_provider,
            knowledge_governance_provider=knowledge_governance_provider,
            enterprise_ai_readiness_provider=enterprise_ai_readiness_provider,
            ai_workflow_diagnostics_provider=ai_workflow_diagnostics_provider,
            director_dashboard_provider=director_dashboard_provider,
            director_platform_provider=director_platform_provider,
            creative_planning_provider=creative_planning_provider,
            knowledge_foundation_provider=knowledge_foundation_provider,
            workflow_intelligence_provider=workflow_intelligence_provider,
            planning_summary_provider=planning_summary_provider,
            multi_agent_provider=multi_agent_provider,
            creative_knowledge_provider=creative_knowledge_provider,
            director_intelligence_provider=director_intelligence_provider,
            review_pipeline_provider=review_pipeline_provider,
            knowledge_relationship_provider=knowledge_relationship_provider,
            director_reliability_v3_provider=director_reliability_v3_provider,
            creative_governance_provider=creative_governance_provider,
            knowledge_integrity_provider=knowledge_integrity_provider,
            production_readiness_provider=production_readiness_provider,
            release_readiness_provider=release_readiness_provider,
            collaboration_foundation_provider=collaboration_foundation_provider,
            knowledge_evolution_provider=knowledge_evolution_provider,
            operations_foundation_provider=operations_foundation_provider,
            developer_productivity_provider=developer_productivity_provider,
            project_metrics_provider=project_metrics_provider,
            creative_review_provider=creative_review_provider,
            knowledge_analytics_provider=knowledge_analytics_provider,
            operations_intelligence_provider=operations_intelligence_provider,
            developer_experience_provider=developer_experience_provider,
            workflow_efficiency_provider=workflow_efficiency_provider,
            creative_governance_v31_provider=creative_governance_v31_provider,
            knowledge_reliability_provider=knowledge_reliability_provider,
            operational_readiness_v31_provider=operational_readiness_v31_provider,
            release_quality_provider=release_quality_provider,
            compatibility_validation_provider=compatibility_validation_provider,
            creative_studio_v32_provider=creative_studio_v32_provider,
            asset_intelligence_v32_provider=asset_intelligence_v32_provider,
            workflow_profiles_v32_provider=workflow_profiles_v32_provider,
            production_analytics_v32_provider=production_analytics_v32_provider,
            workspace_dashboard_v32_provider=workspace_dashboard_v32_provider,
            creative_workspace_v32_provider=creative_workspace_v32_provider,
            asset_analytics_v32_provider=asset_analytics_v32_provider,
            workflow_intelligence_v32_provider=workflow_intelligence_v32_provider,
            production_insights_v32_provider=production_insights_v32_provider,
            pipeline_analysis_v32_provider=pipeline_analysis_v32_provider,
            creative_reliability_v32_provider=creative_reliability_v32_provider,
            asset_governance_v32_provider=asset_governance_v32_provider,
            operational_intelligence_v32_provider=operational_intelligence_v32_provider,
            release_readiness_v32_provider=release_readiness_v32_provider,
            compatibility_validation_v32_provider=compatibility_validation_v32_provider,
            production_pipeline_v33_provider=production_pipeline_v33_provider,
            quality_intelligence_v33_provider=quality_intelligence_v33_provider,
            asset_lifecycle_v33_provider=asset_lifecycle_v33_provider,
            project_intelligence_v33_provider=project_intelligence_v33_provider,
            production_intelligence_v33_provider=production_intelligence_v33_provider,
            quality_analytics_v33_provider=quality_analytics_v33_provider,
            asset_intelligence_v33_provider=asset_intelligence_v33_provider,
            project_operations_v33_provider=project_operations_v33_provider,
            production_governance_v33_provider=production_governance_v33_provider,
            quality_governance_v33_provider=quality_governance_v33_provider,
            asset_governance_v33_provider=asset_governance_v33_provider,
            project_governance_v33_provider=project_governance_v33_provider,
            knowledge_platform_v34_provider=knowledge_platform_v34_provider,
            production_operations_v34_provider=production_operations_v34_provider,
            organization_intelligence_v34_provider=organization_intelligence_v34_provider,
            release_intelligence_v34_provider=release_intelligence_v34_provider,
            knowledge_intelligence_v34_provider=knowledge_intelligence_v34_provider,
            production_optimization_v34_provider=production_optimization_v34_provider,
            organization_analytics_v34_provider=organization_analytics_v34_provider,
            release_analytics_v34_provider=release_analytics_v34_provider,
            knowledge_governance_v34_provider=knowledge_governance_v34_provider,
            production_governance_v34_provider=production_governance_v34_provider,
            organization_governance_v34_provider=organization_governance_v34_provider,
            release_governance_v34_provider=release_governance_v34_provider,
            knowledge_graph_v35_provider=knowledge_graph_v35_provider,
            creative_intelligence_v35_provider=creative_intelligence_v35_provider,
            production_intelligence_v35_provider=production_intelligence_v35_provider,
            platform_analytics_v35_provider=platform_analytics_v35_provider,
            knowledge_insights_v35_provider=knowledge_insights_v35_provider,
            creative_analytics_v35_provider=creative_analytics_v35_provider,
            production_analytics_v35_provider=production_analytics_v35_provider,
            executive_analytics_v35_provider=executive_analytics_v35_provider,
            knowledge_governance_v35_provider=knowledge_governance_v35_provider,
            creative_governance_v35_provider=creative_governance_v35_provider,
            production_governance_v35_provider=production_governance_v35_provider,
            platform_governance_v35_provider=platform_governance_v35_provider,
        ),
        McpResourceProvider(service),
        McpPromptLoader(configured_prompt_directory),
    )
