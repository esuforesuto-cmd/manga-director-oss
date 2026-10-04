"""Tool definitions, schema validation, and safe handler dispatch."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from manga_director.mcp.application import MangaApplicationService
from manga_director.mcp.contracts import (
    ApprovePageInput,
    ChapterInput,
    CreateProjectInput,
    EmptyInput,
    McpToolResult,
    PageInput,
    ProjectInput,
)
from manga_director.mcp.errors import map_error

LOGGER = logging.getLogger(__name__)
ToolHandler = Callable[[Any], Any]


class ToolDefinition:
    def __init__(
        self, name: str, description: str, input_model: type[BaseModel], handler: ToolHandler
    ) -> None:
        self.name = name
        self.description = description
        self.input_model = input_model
        self.handler = handler

    def as_mcp_tool(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_model.model_json_schema(),
        }


class ToolRegistry:
    """Registry that validates tool input before an Application Service is called."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        if definition.name in self._tools:
            raise ValueError(f"MCP tool '{definition.name}' is already registered.")
        self._tools[definition.name] = definition

    def list(self) -> list[dict[str, Any]]:
        return [self._tools[name].as_mcp_tool() for name in sorted(self._tools)]

    def invoke(self, name: str, arguments: dict[str, Any]) -> McpToolResult:
        try:
            definition = self._tools[name]
        except KeyError:
            return McpToolResult(
                success=False,
                operation=name,
                errors=[f"validation_error: unknown MCP tool '{name}'."],
            )
        try:
            validated = definition.input_model.model_validate(arguments)
            value = definition.handler(validated)
            state = _state(value)
            return McpToolResult(
                success=True,
                operation=name,
                state=state,
                data=_json_value(value),
                messages=[f"{name} completed."],
            )
        except PydanticValidationError as exc:
            return McpToolResult(
                success=False,
                operation=name,
                errors=[f"validation_error: {exc.errors(include_url=False, include_input=False)}"],
            )
        except Exception as exc:
            LOGGER.exception("MCP tool failed: %s", name)
            return map_error(name, exc)


def default_tool_registry(
    service: MangaApplicationService,
    *,
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
) -> ToolRegistry:
    """Register the reviewed MCP tool surface with only Application Service handlers."""
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            "create_project",
            "Create a Project with one Draft page.",
            CreateProjectInput,
            lambda item: service.create_project(
                item.project_id, item.title, item.page_number, item.metadata
            ),
        )
    )
    _register_project_tools(registry, service)
    _register_page_tools(registry, service)
    _register_diagnostic_tools(
        registry,
        diagnostics_provider,
        health_provider,
        provider_health_provider,
        backend_health_provider,
        repository_check_provider,
        planning_provider,
        provider_selection_provider,
        analytics_provider,
        enterprise_provider,
        executive_provider,
        assurance_provider,
        provider_governance_provider,
        dashboard_provider,
        director_provider,
        knowledge_provider,
        orchestration_provider,
        director_reliability_provider,
        knowledge_governance_provider,
        enterprise_ai_readiness_provider,
        ai_workflow_diagnostics_provider,
        director_dashboard_provider,
        director_platform_provider,
        creative_planning_provider,
        knowledge_foundation_provider,
        workflow_intelligence_provider,
        planning_summary_provider,
        multi_agent_provider,
        creative_knowledge_provider,
        director_intelligence_provider,
        review_pipeline_provider,
        knowledge_relationship_provider,
        director_reliability_v3_provider,
        creative_governance_provider,
        knowledge_integrity_provider,
        production_readiness_provider,
        release_readiness_provider,
        collaboration_foundation_provider,
        knowledge_evolution_provider,
        operations_foundation_provider,
        developer_productivity_provider,
        project_metrics_provider,
        creative_review_provider,
        knowledge_analytics_provider,
        operations_intelligence_provider,
        developer_experience_provider,
        workflow_efficiency_provider,
        creative_governance_v31_provider,
        knowledge_reliability_provider,
        operational_readiness_v31_provider,
        release_quality_provider,
        compatibility_validation_provider,
        creative_studio_v32_provider,
        asset_intelligence_v32_provider,
        workflow_profiles_v32_provider,
        production_analytics_v32_provider,
        workspace_dashboard_v32_provider,
        creative_workspace_v32_provider,
        asset_analytics_v32_provider,
        workflow_intelligence_v32_provider,
        production_insights_v32_provider,
        pipeline_analysis_v32_provider,
        creative_reliability_v32_provider,
        asset_governance_v32_provider,
        operational_intelligence_v32_provider,
        release_readiness_v32_provider,
        compatibility_validation_v32_provider,
        production_pipeline_v33_provider,
        quality_intelligence_v33_provider,
        asset_lifecycle_v33_provider,
        project_intelligence_v33_provider,
        production_intelligence_v33_provider,
        quality_analytics_v33_provider,
        asset_intelligence_v33_provider,
        project_operations_v33_provider,
        production_governance_v33_provider,
        quality_governance_v33_provider,
        asset_governance_v33_provider,
        project_governance_v33_provider,
        knowledge_platform_v34_provider,
        production_operations_v34_provider,
        organization_intelligence_v34_provider,
        release_intelligence_v34_provider,
        knowledge_intelligence_v34_provider,
        production_optimization_v34_provider,
        organization_analytics_v34_provider,
        release_analytics_v34_provider,
        knowledge_governance_v34_provider,
        production_governance_v34_provider,
        organization_governance_v34_provider,
        release_governance_v34_provider,
        knowledge_graph_v35_provider,
        creative_intelligence_v35_provider,
        production_intelligence_v35_provider,
        platform_analytics_v35_provider,
        knowledge_insights_v35_provider,
        creative_analytics_v35_provider,
        production_analytics_v35_provider,
        executive_analytics_v35_provider,
        knowledge_governance_v35_provider,
        creative_governance_v35_provider,
        production_governance_v35_provider,
        platform_governance_v35_provider,
    )
    return registry


def _register_diagnostic_tools(
    registry: ToolRegistry,
    diagnostics_provider: Callable[[], Any] | None,
    health_provider: Callable[[], Any] | None,
    provider_health_provider: Callable[[], Any] | None,
    backend_health_provider: Callable[[], Any] | None,
    repository_check_provider: Callable[[], Any] | None,
    planning_provider: Callable[[], Any] | None,
    provider_selection_provider: Callable[[], Any] | None,
    analytics_provider: Callable[[], Any] | None,
    enterprise_provider: Callable[[], Any] | None,
    executive_provider: Callable[[], Any] | None,
    assurance_provider: Callable[[], Any] | None,
    provider_governance_provider: Callable[[], Any] | None,
    dashboard_provider: Callable[[], Any] | None,
    director_provider: Callable[[], Any] | None,
    knowledge_provider: Callable[[], Any] | None,
    orchestration_provider: Callable[[], Any] | None,
    director_reliability_provider: Callable[[], Any] | None,
    knowledge_governance_provider: Callable[[], Any] | None,
    enterprise_ai_readiness_provider: Callable[[], Any] | None,
    ai_workflow_diagnostics_provider: Callable[[], Any] | None,
    director_dashboard_provider: Callable[[], Any] | None,
    director_platform_provider: Callable[[], Any] | None,
    creative_planning_provider: Callable[[], Any] | None,
    knowledge_foundation_provider: Callable[[], Any] | None,
    workflow_intelligence_provider: Callable[[], Any] | None,
    planning_summary_provider: Callable[[], Any] | None,
    multi_agent_provider: Callable[[], Any] | None,
    creative_knowledge_provider: Callable[[], Any] | None,
    director_intelligence_provider: Callable[[], Any] | None,
    review_pipeline_provider: Callable[[], Any] | None,
    knowledge_relationship_provider: Callable[[], Any] | None,
    director_reliability_v3_provider: Callable[[], Any] | None,
    creative_governance_provider: Callable[[], Any] | None,
    knowledge_integrity_provider: Callable[[], Any] | None,
    production_readiness_provider: Callable[[], Any] | None,
    release_readiness_provider: Callable[[], Any] | None,
    collaboration_foundation_provider: Callable[[], Any] | None,
    knowledge_evolution_provider: Callable[[], Any] | None,
    operations_foundation_provider: Callable[[], Any] | None,
    developer_productivity_provider: Callable[[], Any] | None,
    project_metrics_provider: Callable[[], Any] | None,
    creative_review_provider: Callable[[], Any] | None,
    knowledge_analytics_provider: Callable[[], Any] | None,
    operations_intelligence_provider: Callable[[], Any] | None,
    developer_experience_provider: Callable[[], Any] | None,
    workflow_efficiency_provider: Callable[[], Any] | None,
    creative_governance_v31_provider: Callable[[], Any] | None,
    knowledge_reliability_provider: Callable[[], Any] | None,
    operational_readiness_v31_provider: Callable[[], Any] | None,
    release_quality_provider: Callable[[], Any] | None,
    compatibility_validation_provider: Callable[[], Any] | None,
    creative_studio_v32_provider: Callable[[], Any] | None,
    asset_intelligence_v32_provider: Callable[[], Any] | None,
    workflow_profiles_v32_provider: Callable[[], Any] | None,
    production_analytics_v32_provider: Callable[[], Any] | None,
    workspace_dashboard_v32_provider: Callable[[], Any] | None,
    creative_workspace_v32_provider: Callable[[], Any] | None,
    asset_analytics_v32_provider: Callable[[], Any] | None,
    workflow_intelligence_v32_provider: Callable[[], Any] | None,
    production_insights_v32_provider: Callable[[], Any] | None,
    pipeline_analysis_v32_provider: Callable[[], Any] | None,
    creative_reliability_v32_provider: Callable[[], Any] | None,
    asset_governance_v32_provider: Callable[[], Any] | None,
    operational_intelligence_v32_provider: Callable[[], Any] | None,
    release_readiness_v32_provider: Callable[[], Any] | None,
    compatibility_validation_v32_provider: Callable[[], Any] | None,
    production_pipeline_v33_provider: Callable[[], Any] | None,
    quality_intelligence_v33_provider: Callable[[], Any] | None,
    asset_lifecycle_v33_provider: Callable[[], Any] | None,
    project_intelligence_v33_provider: Callable[[], Any] | None,
    production_intelligence_v33_provider: Callable[[], Any] | None,
    quality_analytics_v33_provider: Callable[[], Any] | None,
    asset_intelligence_v33_provider: Callable[[], Any] | None,
    project_operations_v33_provider: Callable[[], Any] | None,
    production_governance_v33_provider: Callable[[], Any] | None,
    quality_governance_v33_provider: Callable[[], Any] | None,
    asset_governance_v33_provider: Callable[[], Any] | None,
    project_governance_v33_provider: Callable[[], Any] | None,
    knowledge_platform_v34_provider: Callable[[], Any] | None,
    production_operations_v34_provider: Callable[[], Any] | None,
    organization_intelligence_v34_provider: Callable[[], Any] | None,
    release_intelligence_v34_provider: Callable[[], Any] | None,
    knowledge_intelligence_v34_provider: Callable[[], Any] | None,
    production_optimization_v34_provider: Callable[[], Any] | None,
    organization_analytics_v34_provider: Callable[[], Any] | None,
    release_analytics_v34_provider: Callable[[], Any] | None,
    knowledge_governance_v34_provider: Callable[[], Any] | None,
    production_governance_v34_provider: Callable[[], Any] | None,
    organization_governance_v34_provider: Callable[[], Any] | None,
    release_governance_v34_provider: Callable[[], Any] | None,
    knowledge_graph_v35_provider: Callable[[], Any] | None,
    creative_intelligence_v35_provider: Callable[[], Any] | None,
    production_intelligence_v35_provider: Callable[[], Any] | None,
    platform_analytics_v35_provider: Callable[[], Any] | None,
    knowledge_insights_v35_provider: Callable[[], Any] | None,
    creative_analytics_v35_provider: Callable[[], Any] | None,
    production_analytics_v35_provider: Callable[[], Any] | None,
    executive_analytics_v35_provider: Callable[[], Any] | None,
    knowledge_governance_v35_provider: Callable[[], Any] | None,
    creative_governance_v35_provider: Callable[[], Any] | None,
    production_governance_v35_provider: Callable[[], Any] | None,
    platform_governance_v35_provider: Callable[[], Any] | None,
) -> None:
    registry.register(
        ToolDefinition(
            "creative_reliability_v32",
            "Return v3.2 Creative Reliability diagnostics without workflow execution or approval.",
            EmptyInput,
            _optional_diagnostic(
                creative_reliability_v32_provider,
                {"available": False, "reason": "v3.2 Creative Reliability not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "asset_governance_v32",
            "Return redacted v3.2 Asset Governance diagnostics without repository mutation.",
            EmptyInput,
            _optional_diagnostic(
                asset_governance_v32_provider,
                {"available": False, "reason": "v3.2 Asset Governance not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "operational_intelligence_v32",
            "Return v3.2 Operational Intelligence without runtime modification.",
            EmptyInput,
            _optional_diagnostic(
                operational_intelligence_v32_provider,
                {"available": False, "reason": "v3.2 Operational Intelligence not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "release_readiness_v32",
            "Return v3.2 Release Readiness evidence without release authorization.",
            EmptyInput,
            _optional_diagnostic(
                release_readiness_v32_provider,
                {"available": False, "reason": "v3.2 Release Readiness not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "compatibility_validation_v32",
            "Return v3.2 compatibility evidence without changing public interfaces.",
            EmptyInput,
            _optional_diagnostic(
                compatibility_validation_v32_provider,
                {"available": False, "reason": "v3.2 Compatibility Validation not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "creative_workspace_v32",
            "Return v3.2 Creative Workspace analysis without task execution or approval.",
            EmptyInput,
            _optional_diagnostic(
                creative_workspace_v32_provider,
                {"available": False, "reason": "v3.2 Creative Workspace not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "asset_analytics_v32",
            "Return redacted v3.2 Asset Analytics without repository mutation.",
            EmptyInput,
            _optional_diagnostic(
                asset_analytics_v32_provider,
                {"available": False, "reason": "v3.2 Asset Analytics not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "workflow_intelligence_v32",
            "Return v3.2 Workflow Intelligence without a state transition.",
            EmptyInput,
            _optional_diagnostic(
                workflow_intelligence_v32_provider,
                {"available": False, "reason": "v3.2 Workflow Intelligence not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "production_insights_v32",
            "Return v3.2 Production Insights without runtime automation.",
            EmptyInput,
            _optional_diagnostic(
                production_insights_v32_provider,
                {"available": False, "reason": "v3.2 Production Insights not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "pipeline_analysis_v32",
            "Return v3.2 Pipeline analysis without profile application or workflow execution.",
            EmptyInput,
            _optional_diagnostic(
                pipeline_analysis_v32_provider,
                {"available": False, "reason": "v3.2 Pipeline Analysis not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "creative_studio_v32",
            "Return v3.2 Studio planning evidence without workflow execution.",
            EmptyInput,
            _optional_diagnostic(
                creative_studio_v32_provider,
                {"available": False, "reason": "v3.2 Creative Studio not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "asset_intelligence_v32",
            "Return redacted v3.2 Asset intelligence without repository mutation.",
            EmptyInput,
            _optional_diagnostic(
                asset_intelligence_v32_provider,
                {"available": False, "reason": "v3.2 Asset Intelligence not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "workflow_profiles_v32",
            "Return v3.2 StateMachine profile evidence without transition.",
            EmptyInput,
            _optional_diagnostic(
                workflow_profiles_v32_provider,
                {"available": False, "reason": "v3.2 Workflow Profiles not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "production_analytics_v32",
            "Return v3.2 Production analytics without runtime automation.",
            EmptyInput,
            _optional_diagnostic(
                production_analytics_v32_provider,
                {"available": False, "reason": "v3.2 Production Analytics not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "workspace_dashboard_v32",
            "Return a v3.2 workspace dashboard DTO without persistence changes.",
            EmptyInput,
            _optional_diagnostic(
                workspace_dashboard_v32_provider,
                {"available": False, "reason": "v3.2 Workspace Dashboard not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "creative_governance_v31",
            "Return v3.1 creative governance diagnostics without approval or remediation.",
            EmptyInput,
            _optional_diagnostic(
                creative_governance_v31_provider,
                {"available": False, "reason": "v3.1 Creative Governance not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "knowledge_reliability",
            "Return v3.1 read-only Knowledge reliability diagnostics.",
            EmptyInput,
            _optional_diagnostic(
                knowledge_reliability_provider,
                {"available": False, "reason": "v3.1 Knowledge Reliability not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "operational_readiness_v31",
            "Return v3.1 operational readiness diagnostics without deployment.",
            EmptyInput,
            _optional_diagnostic(
                operational_readiness_v31_provider,
                {"available": False, "reason": "v3.1 Operational Readiness not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "release_quality",
            "Return v3.1 release-quality diagnostics without release authorization.",
            EmptyInput,
            _optional_diagnostic(
                release_quality_provider,
                {"available": False, "reason": "v3.1 Release Quality not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "compatibility_validation",
            "Return v3.1 compatibility evidence without interface changes.",
            EmptyInput,
            _optional_diagnostic(
                compatibility_validation_provider,
                {"available": False, "reason": "v3.1 Compatibility Validation not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "creative_review",
            "Return v3.1 diagnostic creative review evidence without approval.",
            EmptyInput,
            _optional_diagnostic(
                creative_review_provider,
                {"available": False, "reason": "v3.1 Creative Review not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "knowledge_analytics",
            "Return v3.1 redacted Knowledge analytics without repository mutation.",
            EmptyInput,
            _optional_diagnostic(
                knowledge_analytics_provider,
                {"available": False, "reason": "v3.1 Knowledge Analytics not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "operations_intelligence",
            "Return v3.1 operations insights without runtime modification.",
            EmptyInput,
            _optional_diagnostic(
                operations_intelligence_provider,
                {"available": False, "reason": "v3.1 Operations Intelligence not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "developer_experience",
            "Return v3.1 developer experience guidance without applying changes.",
            EmptyInput,
            _optional_diagnostic(
                developer_experience_provider,
                {"available": False, "reason": "v3.1 Developer Experience not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "workflow_efficiency",
            "Return one-Page workflow efficiency evidence without workflow execution.",
            EmptyInput,
            _optional_diagnostic(
                workflow_efficiency_provider,
                {"available": False, "reason": "v3.1 Workflow Efficiency not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "collaboration_foundation",
            "Return a v3.1 human collaboration DTO without Agent execution or approval.",
            EmptyInput,
            _optional_diagnostic(
                collaboration_foundation_provider,
                {"available": False, "reason": "v3.1 Collaboration Foundation not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "knowledge_evolution",
            "Return a v3.1 read-only Knowledge evolution DTO without repository mutation.",
            EmptyInput,
            _optional_diagnostic(
                knowledge_evolution_provider,
                {"available": False, "reason": "v3.1 Knowledge Evolution not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "operations_foundation",
            "Return v3.1 Operations metrics without runtime automation.",
            EmptyInput,
            _optional_diagnostic(
                operations_foundation_provider,
                {"available": False, "reason": "v3.1 Operations Foundation not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "developer_productivity",
            "Return v3.1 template descriptors without generating files.",
            EmptyInput,
            _optional_diagnostic(
                developer_productivity_provider,
                {"available": False, "reason": "v3.1 Developer Productivity not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "project_metrics",
            "Return v3.1 aggregate Project metrics without multi-page execution.",
            EmptyInput,
            _optional_diagnostic(
                project_metrics_provider,
                {"available": False, "reason": "v3.1 Project Metrics not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "director_reliability_v3",
            "Return a v3 Director reliability validation DTO without workflow execution.",
            EmptyInput,
            _optional_diagnostic(
                director_reliability_v3_provider,
                {"available": False, "reason": "v3 Director Reliability not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "creative_governance",
            "Return a v3 Creative governance and audit DTO without artifact changes.",
            EmptyInput,
            _optional_diagnostic(
                creative_governance_provider,
                {"available": False, "reason": "v3 Creative Governance not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "knowledge_integrity",
            "Return a v3 read-only Knowledge integrity and risk DTO.",
            EmptyInput,
            _optional_diagnostic(
                knowledge_integrity_provider,
                {"available": False, "reason": "v3 Knowledge Integrity not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "production_readiness",
            "Return a v3 deployment-readiness DTO without deployment.",
            EmptyInput,
            _optional_diagnostic(
                production_readiness_provider,
                {"available": False, "reason": "v3 Production Readiness not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "release_readiness",
            "Return a v3 release dashboard without release authorization.",
            EmptyInput,
            _optional_diagnostic(
                release_readiness_provider,
                {"available": False, "reason": "v3 Release Readiness not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "multi_agent_foundation",
            "Return a non-executing multi-agent collaboration plan DTO.",
            EmptyInput,
            _optional_diagnostic(
                multi_agent_provider,
                {"available": False, "reason": "v3 Multi-Agent Foundation not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "creative_knowledge",
            "Return a repository-derived v3 Creative Knowledge DTO.",
            EmptyInput,
            _optional_diagnostic(
                creative_knowledge_provider,
                {"available": False, "reason": "v3 Creative Knowledge not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "director_intelligence",
            "Return diagnostic creative decisions, alternatives, risks, and recommendations.",
            EmptyInput,
            _optional_diagnostic(
                director_intelligence_provider,
                {"available": False, "reason": "v3 Director Intelligence not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "review_pipeline",
            "Return diagnostic story, storyboard, consistency, and quality review evidence.",
            EmptyInput,
            _optional_diagnostic(
                review_pipeline_provider,
                {"available": False, "reason": "v3 Review Pipeline not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "knowledge_relationship",
            "Return a read-only Creative Knowledge relationship graph DTO.",
            EmptyInput,
            _optional_diagnostic(
                knowledge_relationship_provider,
                {"available": False, "reason": "v3 Knowledge Relationship not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "director_platform",
            "Return a v3 advisory Director Platform session DTO.",
            EmptyInput,
            _optional_diagnostic(
                director_platform_provider,
                {"available": False, "reason": "v3 Director Platform not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "creative_planning",
            "Return a v3 creative planning DTO without image generation.",
            EmptyInput,
            _optional_diagnostic(
                creative_planning_provider,
                {"available": False, "reason": "v3 Creative Planning not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "knowledge_foundation",
            "Return a repository-derived v3 Knowledge Foundation DTO.",
            EmptyInput,
            _optional_diagnostic(
                knowledge_foundation_provider,
                {"available": False, "reason": "v3 Knowledge Foundation not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "workflow_intelligence",
            "Return a v3 diagnostic Workflow Intelligence DTO.",
            EmptyInput,
            _optional_diagnostic(
                workflow_intelligence_provider,
                {"available": False, "reason": "v3 Workflow Intelligence not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "planning_foundation_summary",
            "Return a compact v3 planning summary with no execution capability.",
            EmptyInput,
            _optional_diagnostic(
                planning_summary_provider,
                {"available": False, "reason": "v3 planning summary not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "director_planning",
            "Return a read-only AI Director plan DTO.",
            EmptyInput,
            _optional_diagnostic(
                director_provider, {"available": False, "reason": "AI Director not configured"}
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "knowledge_summary",
            "Return a repository-derived read-only Knowledge DTO.",
            EmptyInput,
            _optional_diagnostic(
                knowledge_provider,
                {"available": False, "reason": "Knowledge service not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "workflow_orchestration",
            "Return a non-executing one-page orchestration DTO.",
            EmptyInput,
            _optional_diagnostic(
                orchestration_provider,
                {"available": False, "reason": "Workflow Orchestration not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "director_reliability",
            "Return read-only AI Director integrity, consistency, trace, and readiness evidence.",
            EmptyInput,
            _optional_diagnostic(
                director_reliability_provider,
                {"available": False, "reason": "AI Director reliability not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "knowledge_governance",
            "Return read-only Knowledge policy, integrity, lifecycle, quality, and risk evidence.",
            EmptyInput,
            _optional_diagnostic(
                knowledge_governance_provider,
                {"available": False, "reason": "Knowledge governance not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "enterprise_ai_readiness",
            "Return a checklist-only enterprise AI readiness DTO.",
            EmptyInput,
            _optional_diagnostic(
                enterprise_ai_readiness_provider,
                {"available": False, "reason": "enterprise AI readiness not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "ai_workflow_diagnostics",
            "Return safe AI Director, Knowledge, planning, workflow, and architecture diagnostics.",
            EmptyInput,
            _optional_diagnostic(
                ai_workflow_diagnostics_provider,
                {"available": False, "reason": "AI workflow diagnostics not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "director_dashboard",
            "Return a read-only Director, Knowledge, Workflow, Enterprise, and Release dashboard DTO.",
            EmptyInput,
            _optional_diagnostic(
                director_dashboard_provider,
                {"available": False, "reason": "Director dashboard not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "health_status",
            "Return a safe runtime health DTO.",
            EmptyInput,
            _optional_diagnostic(health_provider, {"healthy": True, "mode": "not_configured"}),
        )
    )
    registry.register(
        ToolDefinition(
            "workflow_reliability",
            "Return a read-only AI workflow integrity, risk, and readiness DTO.",
            EmptyInput,
            _optional_diagnostic(
                assurance_provider,
                {"available": False, "reason": "workflow assurance not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "provider_governance",
            "Return a local metadata-only Provider governance DTO.",
            EmptyInput,
            _optional_diagnostic(
                provider_governance_provider,
                {"available": False, "reason": "provider governance not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "executive_dashboard",
            "Return a read-only AI workflow, Provider, enterprise, and release dashboard DTO.",
            EmptyInput,
            _optional_diagnostic(
                dashboard_provider,
                {"available": False, "reason": "executive dashboard not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "workflow_analytics",
            "Return a read-only one-page workflow analysis DTO.",
            EmptyInput,
            _optional_diagnostic(
                analytics_provider,
                {"available": False, "reason": "workflow analytics not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "enterprise_diagnostics",
            "Return presentation-independent enterprise diagnostics.",
            EmptyInput,
            _optional_diagnostic(
                enterprise_provider,
                {"available": False, "reason": "enterprise diagnostics not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "executive_analytics",
            "Return a read-only workflow, Provider, and operations executive DTO.",
            EmptyInput,
            _optional_diagnostic(
                executive_provider,
                {"available": False, "reason": "executive analytics not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "planning_summary",
            "Return a read-only one-page workflow planning and intelligence DTO.",
            EmptyInput,
            _optional_diagnostic(
                planning_provider,
                {"available": False, "reason": "workflow planning not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "provider_selection",
            "Return a metadata-only Provider selection recommendation DTO.",
            EmptyInput,
            _optional_diagnostic(
                provider_selection_provider,
                {"available": False, "reason": "provider planning not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "health_summary",
            "Return the complete safe runtime health summary DTO.",
            EmptyInput,
            _optional_diagnostic(health_provider, {"healthy": True, "mode": "not_configured"}),
        )
    )
    registry.register(
        ToolDefinition(
            "provider_health",
            "Return a safe LLM provider health DTO.",
            EmptyInput,
            _optional_diagnostic(
                provider_health_provider,
                {"available": False, "reason": "provider health not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "backend_health",
            "Return a safe image backend health DTO.",
            EmptyInput,
            _optional_diagnostic(
                backend_health_provider,
                {"available": False, "reason": "backend health not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "repository_check",
            "Return a safe repository integrity DTO.",
            EmptyInput,
            _optional_diagnostic(
                repository_check_provider,
                {"available": False, "reason": "repository self-check not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "diagnostics_report",
            "Return a safe runtime diagnostics DTO.",
            EmptyInput,
            _optional_diagnostic(
                diagnostics_provider,
                {"available": False, "reason": "runtime diagnostics not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "system_summary",
            "Return a safe system summary DTO.",
            EmptyInput,
            _system_summary(diagnostics_provider),
        )
    )

    registry.register(
        ToolDefinition(
            "production_pipeline_v33",
            "Return v3.3 Production Pipeline evidence without workflow execution or publishing.",
            EmptyInput,
            _optional_diagnostic(
                production_pipeline_v33_provider,
                {"available": False, "reason": "v3.3 Production Pipeline not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "quality_intelligence_v33",
            "Return v3.3 Quality Intelligence without scoring or approval authority.",
            EmptyInput,
            _optional_diagnostic(
                quality_intelligence_v33_provider,
                {"available": False, "reason": "v3.3 Quality Intelligence not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "asset_lifecycle_v33",
            "Return v3.3 Asset Lifecycle evidence without repository mutation.",
            EmptyInput,
            _optional_diagnostic(
                asset_lifecycle_v33_provider,
                {"available": False, "reason": "v3.3 Asset Lifecycle not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "project_intelligence_v33",
            "Return v3.3 Project Intelligence without scheduling or allocation.",
            EmptyInput,
            _optional_diagnostic(
                project_intelligence_v33_provider,
                {"available": False, "reason": "v3.3 Project Intelligence not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "production_intelligence_v33",
            "Return v3.3 Production Intelligence without workflow modification.",
            EmptyInput,
            _optional_diagnostic(
                production_intelligence_v33_provider,
                {"available": False, "reason": "v3.3 Production Intelligence not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "quality_analytics_v33",
            "Return v3.3 Quality Analytics without scoring or approval authority.",
            EmptyInput,
            _optional_diagnostic(
                quality_analytics_v33_provider,
                {"available": False, "reason": "v3.3 Quality Analytics not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "asset_intelligence_v33",
            "Return redacted v3.3 Asset Intelligence without repository mutation.",
            EmptyInput,
            _optional_diagnostic(
                asset_intelligence_v33_provider,
                {"available": False, "reason": "v3.3 Asset Intelligence not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "project_operations_v33",
            "Return v3.3 Project Operations without scheduling or allocation.",
            EmptyInput,
            _optional_diagnostic(
                project_operations_v33_provider,
                {"available": False, "reason": "v3.3 Project Operations not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "production_governance_v33",
            "Return v3.3 Production Governance without enforcement or workflow execution.",
            EmptyInput,
            _optional_diagnostic(
                production_governance_v33_provider,
                {"available": False, "reason": "v3.3 Production Governance not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "quality_governance_v33",
            "Return v3.3 Quality Governance without scoring or approval authority.",
            EmptyInput,
            _optional_diagnostic(
                quality_governance_v33_provider,
                {"available": False, "reason": "v3.3 Quality Governance not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "asset_governance_v33",
            "Return redacted v3.3 Asset Governance without retention or mutation.",
            EmptyInput,
            _optional_diagnostic(
                asset_governance_v33_provider,
                {"available": False, "reason": "v3.3 Asset Governance not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "project_governance_v33",
            "Return v3.3 Project Governance without scheduling or allocation.",
            EmptyInput,
            _optional_diagnostic(
                project_governance_v33_provider,
                {"available": False, "reason": "v3.3 Project Governance not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "knowledge_platform_v34",
            "Return v3.4 Knowledge Platform evidence without repository mutation.",
            EmptyInput,
            _optional_diagnostic(
                knowledge_platform_v34_provider,
                {"available": False, "reason": "v3.4 Knowledge Platform not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "production_operations_v34",
            "Return v3.4 Production Operations without monitoring or deployment.",
            EmptyInput,
            _optional_diagnostic(
                production_operations_v34_provider,
                {"available": False, "reason": "v3.4 Production Operations not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "organization_intelligence_v34",
            "Return v3.4 Organization Intelligence without personnel action.",
            EmptyInput,
            _optional_diagnostic(
                organization_intelligence_v34_provider,
                {"available": False, "reason": "v3.4 Organization Intelligence not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "release_intelligence_v34",
            "Return v3.4 Release Intelligence without publication authority.",
            EmptyInput,
            _optional_diagnostic(
                release_intelligence_v34_provider,
                {"available": False, "reason": "v3.4 Release Intelligence not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "knowledge_intelligence_v34",
            "Return v3.4 Knowledge Intelligence without repository mutation.",
            EmptyInput,
            _optional_diagnostic(
                knowledge_intelligence_v34_provider,
                {"available": False, "reason": "v3.4 Knowledge Intelligence not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "production_optimization_v34",
            "Return v3.4 Production Optimization without workflow modification.",
            EmptyInput,
            _optional_diagnostic(
                production_optimization_v34_provider,
                {"available": False, "reason": "v3.4 Production Optimization not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "organization_analytics_v34",
            "Return v3.4 Organization Analytics without personnel action.",
            EmptyInput,
            _optional_diagnostic(
                organization_analytics_v34_provider,
                {"available": False, "reason": "v3.4 Organization Analytics not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "release_analytics_v34",
            "Return v3.4 Release Analytics without release authority.",
            EmptyInput,
            _optional_diagnostic(
                release_analytics_v34_provider,
                {"available": False, "reason": "v3.4 Release Analytics not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "knowledge_governance_v34",
            "Return v3.4 Knowledge Governance without repository mutation.",
            EmptyInput,
            _optional_diagnostic(
                knowledge_governance_v34_provider,
                {"available": False, "reason": "v3.4 Knowledge Governance not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "production_governance_v34",
            "Return v3.4 Production Governance without pipeline modification.",
            EmptyInput,
            _optional_diagnostic(
                production_governance_v34_provider,
                {"available": False, "reason": "v3.4 Production Governance not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "organization_governance_v34",
            "Return v3.4 Organization Governance without personnel action.",
            EmptyInput,
            _optional_diagnostic(
                organization_governance_v34_provider,
                {"available": False, "reason": "v3.4 Organization Governance not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "release_governance_v34",
            "Return v3.4 Release Governance without release authority.",
            EmptyInput,
            _optional_diagnostic(
                release_governance_v34_provider,
                {"available": False, "reason": "v3.4 Release Governance not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "knowledge_graph_v35",
            "Return v3.5 Knowledge Graph evidence without graph persistence.",
            EmptyInput,
            _optional_diagnostic(
                knowledge_graph_v35_provider,
                {"available": False, "reason": "v3.5 Knowledge Graph not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "creative_intelligence_v35",
            "Return v3.5 Creative Intelligence without generation or approval.",
            EmptyInput,
            _optional_diagnostic(
                creative_intelligence_v35_provider,
                {"available": False, "reason": "v3.5 Creative Intelligence not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "production_intelligence_v35",
            "Return v3.5 Production Intelligence without scheduling or deployment.",
            EmptyInput,
            _optional_diagnostic(
                production_intelligence_v35_provider,
                {"available": False, "reason": "v3.5 Production Intelligence not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "platform_analytics_v35",
            "Return v3.5 Platform Analytics without collection or external action.",
            EmptyInput,
            _optional_diagnostic(
                platform_analytics_v35_provider,
                {"available": False, "reason": "v3.5 Platform Analytics not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "knowledge_insights_v35",
            "Return v3.5 Knowledge Analytics without graph mutation.",
            EmptyInput,
            _optional_diagnostic(
                knowledge_insights_v35_provider,
                {"available": False, "reason": "v3.5 Knowledge Insights not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "creative_analytics_v35",
            "Return v3.5 Creative Analytics without generation or approval.",
            EmptyInput,
            _optional_diagnostic(
                creative_analytics_v35_provider,
                {"available": False, "reason": "v3.5 Creative Analytics not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "production_analytics_v35",
            "Return v3.5 Production Analytics without scheduling or deployment.",
            EmptyInput,
            _optional_diagnostic(
                production_analytics_v35_provider,
                {"available": False, "reason": "v3.5 Production Analytics not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "executive_analytics_v35",
            "Return v3.5 Executive Analytics without collection or external action.",
            EmptyInput,
            _optional_diagnostic(
                executive_analytics_v35_provider,
                {"available": False, "reason": "v3.5 Executive Analytics not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "knowledge_governance_v35",
            "Return v3.5 Knowledge Governance without policy enforcement.",
            EmptyInput,
            _optional_diagnostic(
                knowledge_governance_v35_provider,
                {"available": False, "reason": "v3.5 Knowledge Governance not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "creative_governance_v35",
            "Return v3.5 Creative Governance without creative or approval authority.",
            EmptyInput,
            _optional_diagnostic(
                creative_governance_v35_provider,
                {"available": False, "reason": "v3.5 Creative Governance not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "production_governance_v35",
            "Return v3.5 Production Governance without workflow or deployment authority.",
            EmptyInput,
            _optional_diagnostic(
                production_governance_v35_provider,
                {"available": False, "reason": "v3.5 Production Governance not configured"},
            ),
        )
    )
    registry.register(
        ToolDefinition(
            "platform_governance_v35",
            "Return v3.5 Platform Governance without monitoring or external action.",
            EmptyInput,
            _optional_diagnostic(
                platform_governance_v35_provider,
                {"available": False, "reason": "v3.5 Platform Governance not configured"},
            ),
        )
    )


def _optional_diagnostic(
    provider: Callable[[], Any] | None, unavailable: dict[str, object]
) -> ToolHandler:
    def handler(_: Any) -> Any:
        return provider() if provider is not None else unavailable

    return handler


def _system_summary(diagnostics_provider: Callable[[], Any] | None) -> ToolHandler:
    def handler(_: Any) -> Any:
        report = _optional_diagnostic(
            diagnostics_provider,
            {"available": False, "reason": "runtime diagnostics not configured"},
        )(None)
        if hasattr(report, "system"):
            return {"system": report.system}
        return report

    return handler


def _register_project_tools(registry: ToolRegistry, service: MangaApplicationService) -> None:
    def list_projects(_: Any) -> Any:
        return service.list_projects()

    def get_project(item: ProjectInput) -> Any:
        return service.get_project(item.project_id)

    def delete_project(item: ProjectInput) -> Any:
        return service.delete_project(item.project_id)

    def project_status(item: ProjectInput) -> Any:
        return service.get_project_status(item.project_id)

    def run_project(item: ProjectInput) -> Any:
        return service.run_project(item.project_id)

    def resume_project(item: ProjectInput) -> Any:
        return service.resume_project(item.project_id)

    def run_chapter(item: ChapterInput) -> Any:
        return service.run_chapter(item.project_id, item.chapter_id)

    def chapter_status(item: ChapterInput) -> Any:
        return service.get_chapter_status(item.project_id, item.chapter_id)

    registry.register(
        ToolDefinition("list_projects", "List persisted Projects.", EmptyInput, list_projects)
    )
    registry.register(
        ToolDefinition("get_project", "Read one persisted Project.", ProjectInput, get_project)
    )
    registry.register(
        ToolDefinition(
            "delete_project", "Delete one persisted Project.", ProjectInput, delete_project
        )
    )
    registry.register(
        ToolDefinition(
            "get_project_status",
            "Read Project workflow progress.",
            ProjectInput,
            project_status,
        )
    )
    registry.register(
        ToolDefinition("run_project", "Run one scheduled Project page.", ProjectInput, run_project)
    )
    registry.register(
        ToolDefinition(
            "resume_project", "Resume one scheduled Project page.", ProjectInput, resume_project
        )
    )
    registry.register(
        ToolDefinition("run_chapter", "Run one scheduled Chapter page.", ChapterInput, run_chapter)
    )
    registry.register(
        ToolDefinition(
            "get_chapter_status",
            "Read Chapter workflow progress.",
            ChapterInput,
            chapter_status,
        )
    )


def _register_page_tools(registry: ToolRegistry, service: MangaApplicationService) -> None:
    primary_commands = {
        "design_page": ("design", "Create a page design."),
        "review_page": ("review", "Review a page design."),
        "create_storyboard": ("storyboard", "Create one page storyboard."),
        "build_prompt": ("prompt", "Build one page image prompt."),
        "generate_image": ("generate", "Generate one storyboarded page image."),
        "review_quality": ("quality", "Review generated page quality."),
    }
    for name, (command, description) in primary_commands.items():
        registry.register(
            ToolDefinition(
                name,
                description,
                PageInput,
                _primary_handler(service, command),
            )
        )
    for name, support, description in [
        ("improve_dialogue", "dialogue", "Improve storyboard dialogue."),
        ("check_continuity", "continuity", "Check page continuity."),
    ]:
        registry.register(
            ToolDefinition(
                name,
                description,
                PageInput,
                _support_handler(service, support),
            )
        )
    registry.register(
        ToolDefinition(
            "approve_page",
            "Record explicit human approval after quality review.",
            ApprovePageInput,
            _approve_handler(service),
        )
    )
    registry.register(
        ToolDefinition(
            "get_page_status",
            "Read one Page workflow status.",
            PageInput,
            _page_status_handler(service),
        )
    )


def _json_value(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


def _primary_handler(service: MangaApplicationService, command: str) -> ToolHandler:
    def handler(item: PageInput) -> Any:
        return service.execute_page(command, item.project_id, item.page_number, item.metadata)

    return handler


def _support_handler(service: MangaApplicationService, support: str) -> ToolHandler:
    def handler(item: PageInput) -> Any:
        return service.execute_support(support, item.project_id, item.page_number, item.metadata)

    return handler


def _approve_handler(service: MangaApplicationService) -> ToolHandler:
    def handler(item: ApprovePageInput) -> Any:
        return service.approve_page(
            item.project_id, item.page_number, item.approved_by, item.metadata
        )

    return handler


def _page_status_handler(service: MangaApplicationService) -> ToolHandler:
    def handler(item: PageInput) -> Any:
        return service.get_page_status(item.project_id, item.page_number)

    return handler


def _state(value: Any) -> str | None:
    state = getattr(value, "current_state", None)
    if state is None:
        state = getattr(value, "state", None)
    if state is None:
        return None
    return str(getattr(state, "value", state))
