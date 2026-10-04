"""Read-only v6.0 Knowledge, workflow, automation, and collaboration projections.

The Application-layer services in this module compose caller-supplied evidence
with the existing one-page workflow diagnostics.  They do not persist a graph
or context, dispatch automation, change an assignment, register a service, or
advance the workflow.  The domain ``StateMachine`` remains the only authority
for executable page transitions.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from pydantic import Field

from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.production.v5_7_production_workspace import (
    V57ProductionWorkspaceService,
    WorkflowStateValidationReport,
)
from manga_director.production.v6_0_foundation import (
    CollaborationAssignmentDTO,
    CreativeProductionPlatformCoreReport,
    KnowledgeCoreReferenceDTO,
    ProjectHubReferenceDTO,
    ServiceRegistryEntryDTO,
    V60CreativeProductionPlatformFoundationService,
    WorkspaceHubReferenceDTO,
)
from manga_director.workflow.contracts import WorkflowContext


class KnowledgeGraphNodeDTO(DirectorModel):
    node_id: str
    project_id: str
    kind: Literal["story", "character", "world", "asset", "production", "review"]
    source_reference: str
    provenance: str
    source_record_changed: Literal[False] = False


class KnowledgeGraphEdgeDTO(DirectorModel):
    edge_id: str
    source_node_id: str
    target_node_id: str
    relationship: Literal["references", "depends_on", "reviews", "uses", "contextualizes"]
    edge_persisted: Literal[False] = False


class KnowledgeGraphReport(DirectorModel):
    nodes: tuple[KnowledgeGraphNodeDTO, ...] = ()
    edges: tuple[KnowledgeGraphEdgeDTO, ...] = ()
    valid: bool
    findings: tuple[str, ...] = ()
    graph_projection_built: Literal[True] = True
    graph_persisted: Literal[False] = False
    source_repository_changed: Literal[False] = False
    analysis_only: Literal[True] = True


class ContextFragmentDTO(DirectorModel):
    context_key: str
    project_id: str
    source_reference: str
    category: Literal["story", "character", "world", "timeline", "production", "review"]
    value_present: bool
    source_loaded: Literal[False] = False


class ContextEngineReport(DirectorModel):
    project_id: str
    page_reference: str
    current_state: PageState
    fragments: tuple[ContextFragmentDTO, ...] = ()
    complete: bool
    context_projection_built: Literal[True] = True
    context_persisted: Literal[False] = False
    prompt_generated: Literal[False] = False
    workflow_mutated: Literal[False] = False
    analysis_only: Literal[True] = True


class WorkflowOrchestratorDTO(DirectorModel):
    orchestrator_id: str
    project_id: str
    page_reference: str
    current_state: PageState
    next_command: str | None = None
    human_review_required: Literal[True] = True
    execution_dispatched: Literal[False] = False
    workflow_mutated: Literal[False] = False


class WorkflowOrchestratorReport(DirectorModel):
    orchestrator: WorkflowOrchestratorDTO
    workflow_validation: WorkflowStateValidationReport
    state_machine_authoritative: Literal[True] = True
    recommendation: str
    analysis_only: Literal[True] = True


class V60AutomationRuleDTO(DirectorModel):
    rule_id: str
    event_key: str
    recommended_command: str
    human_review_required: Literal[True] = True
    rule_registered: Literal[False] = False
    action_executed: Literal[False] = False


class AutomationHubReport(DirectorModel):
    rules: tuple[V60AutomationRuleDTO, ...] = ()
    matching_rule_ids: tuple[str, ...] = ()
    next_command: str | None = None
    valid: bool
    automation_dispatched: Literal[False] = False
    automation_persisted: Literal[False] = False
    analysis_only: Literal[True] = True


class CollaborationWorkspaceDTO(DirectorModel):
    workspace_id: str
    project_id: str
    assignment_ids: tuple[str, ...] = ()
    assigned_role_count: int = Field(default=0, ge=0)
    workspace_created: Literal[False] = False
    assignment_changed: Literal[False] = False


class CollaborationWorkspaceReport(DirectorModel):
    workspace: CollaborationWorkspaceDTO
    assignments: tuple[CollaborationAssignmentDTO, ...] = ()
    all_reviews_required: bool
    collaboration_executed: Literal[False] = False
    approval_granted: Literal[False] = False
    analysis_only: Literal[True] = True


class ProductionAnalyticsDTO(DirectorModel):
    project_count: int = Field(default=0, ge=0)
    workspace_count: int = Field(default=0, ge=0)
    knowledge_node_count: int = Field(default=0, ge=0)
    knowledge_edge_count: int = Field(default=0, ge=0)
    assignment_count: int = Field(default=0, ge=0)
    service_count: int = Field(default=0, ge=0)
    current_state: PageState
    quality_review_completed: bool
    metrics_persisted: Literal[False] = False


class V60ProductionAnalyticsReport(DirectorModel):
    analytics: ProductionAnalyticsDTO
    summary: str
    reporting_generated: Literal[True] = True
    decision_automated: Literal[False] = False
    analysis_only: Literal[True] = True


class ServiceDiscoveryDTO(DirectorModel):
    service_id: str
    capability: str
    owner: str
    compatibility: str
    discovery_source: Literal["caller_supplied"] = "caller_supplied"
    runtime_discovery_performed: Literal[False] = False


class ServiceDiscoveryReport(DirectorModel):
    services: tuple[ServiceDiscoveryDTO, ...] = ()
    compatible_service_count: int = Field(default=0, ge=0)
    duplicate_service_ids: tuple[str, ...] = ()
    registry_mutated: Literal[False] = False
    analysis_only: Literal[True] = True


class CreativeProductionPlatformIntelligenceReport(DirectorModel):
    foundation: CreativeProductionPlatformCoreReport
    knowledge_graph: KnowledgeGraphReport
    context: ContextEngineReport
    workflow: WorkflowOrchestratorReport
    automation: AutomationHubReport
    collaboration: CollaborationWorkspaceReport
    analytics: V60ProductionAnalyticsReport
    services: ServiceDiscoveryReport
    v5_compatibility_preserved: Literal[True] = True
    automatic_action_taken: Literal[False] = False
    analysis_only: Literal[True] = True


class V60CreativeProductionPlatformIntelligenceService:
    """Compose bounded v6.0 intelligence diagnostics without side effects."""

    def __init__(self) -> None:
        self._foundation = V60CreativeProductionPlatformFoundationService()
        self._workspace = V57ProductionWorkspaceService()

    def knowledge_graph(
        self,
        references: tuple[KnowledgeCoreReferenceDTO, ...] = (),
        edges: tuple[KnowledgeGraphEdgeDTO, ...] = (),
    ) -> KnowledgeGraphReport:
        _require_unique((reference.knowledge_id for reference in references), "knowledge_id")
        _require_unique((edge.edge_id for edge in edges), "edge_id")
        nodes = tuple(
            KnowledgeGraphNodeDTO(
                node_id=reference.knowledge_id,
                project_id=reference.project_id,
                kind=reference.kind,
                source_reference=reference.source_reference,
                provenance=reference.provenance,
            )
            for reference in sorted(references, key=lambda item: item.knowledge_id)
        )
        known_node_ids = {node.node_id for node in nodes}
        findings = tuple(
            f"edge {edge.edge_id} references an unknown node"
            for edge in sorted(edges, key=lambda item: item.edge_id)
            if edge.source_node_id not in known_node_ids or edge.target_node_id not in known_node_ids
        )
        return KnowledgeGraphReport(
            nodes=nodes,
            edges=tuple(sorted(edges, key=lambda item: item.edge_id)),
            valid=not findings,
            findings=findings,
        )

    def context_engine(self, project_id: str, context: WorkflowContext) -> ContextEngineReport:
        production = self._foundation.production_core(project_id, context).production
        categories: dict[
            str, Literal["story", "character", "world", "timeline", "production", "review"]
        ] = {
            "story_context": "story",
            "character_context": "character",
            "world_context": "world",
            "timeline_context": "timeline",
            "production_context": "production",
            "review_context": "review",
        }
        fragments = tuple(
            ContextFragmentDTO(
                context_key=key,
                project_id=project_id,
                source_reference=key,
                category=category,
                value_present=key in context.metadata,
            )
            for key, category in categories.items()
            if key in context.metadata
        )
        required = {"story_context", "character_context", "world_context", "timeline_context"}
        return ContextEngineReport(
            project_id=project_id,
            page_reference=production.page_reference,
            current_state=production.current_state,
            fragments=fragments,
            complete=required.issubset(context.metadata),
        )

    def workflow_orchestrator(
        self, project_id: str, context: WorkflowContext
    ) -> WorkflowOrchestratorReport:
        validation = self._workspace.workflow_state(project_id, context)
        state = validation.state
        recommendation = (
            "No command is available because the Page is approved; retain the completed review."
            if state.next_command is None
            else f"A human may run the StateMachine-validated '{state.next_command}' step."
        )
        return WorkflowOrchestratorReport(
            orchestrator=WorkflowOrchestratorDTO(
                orchestrator_id=f"workflow-orchestrator:{project_id}:{state.page_reference}",
                project_id=project_id,
                page_reference=state.page_reference,
                current_state=state.current_state,
                next_command=state.next_command,
            ),
            workflow_validation=validation,
            recommendation=recommendation,
        )

    def automation_hub(
        self,
        project_id: str,
        context: WorkflowContext,
        rules: tuple[V60AutomationRuleDTO, ...] = (),
    ) -> AutomationHubReport:
        _require_unique((rule.rule_id for rule in rules), "rule_id")
        next_command = self.workflow_orchestrator(project_id, context).orchestrator.next_command
        matching = tuple(
            rule.rule_id
            for rule in sorted(rules, key=lambda item: item.rule_id)
            if rule.recommended_command == next_command
        )
        valid = all(rule.human_review_required and not rule.action_executed for rule in rules)
        return AutomationHubReport(
            rules=tuple(sorted(rules, key=lambda item: item.rule_id)),
            matching_rule_ids=matching,
            next_command=next_command,
            valid=valid,
        )

    def collaboration_workspace(
        self,
        project_id: str,
        workspace_id: str,
        assignments: tuple[CollaborationAssignmentDTO, ...] = (),
    ) -> CollaborationWorkspaceReport:
        _require_unique((assignment.assignment_id for assignment in assignments), "assignment_id")
        scoped = tuple(
            sorted(
                (
                    assignment
                    for assignment in assignments
                    if assignment.project_id == project_id and assignment.workspace_id == workspace_id
                ),
                key=lambda item: item.assignment_id,
            )
        )
        return CollaborationWorkspaceReport(
            workspace=CollaborationWorkspaceDTO(
                workspace_id=workspace_id,
                project_id=project_id,
                assignment_ids=tuple(assignment.assignment_id for assignment in scoped),
                assigned_role_count=len({assignment.role for assignment in scoped}),
            ),
            assignments=scoped,
            all_reviews_required=all(assignment.review_required for assignment in scoped),
        )

    def production_analytics(
        self,
        foundation: CreativeProductionPlatformCoreReport,
        graph: KnowledgeGraphReport,
    ) -> V60ProductionAnalyticsReport:
        production = foundation.production.production
        quality_review_completed = production.current_state in (
            PageState.QUALITY_CHECKED,
            PageState.APPROVED,
        )
        analytics = ProductionAnalyticsDTO(
            project_count=foundation.projects.project_count,
            workspace_count=foundation.workspaces.workspace_count,
            knowledge_node_count=len(graph.nodes),
            knowledge_edge_count=len(graph.edges),
            assignment_count=foundation.collaboration.assignment_count,
            service_count=foundation.services.service_count,
            current_state=production.current_state,
            quality_review_completed=quality_review_completed,
        )
        return V60ProductionAnalyticsReport(
            analytics=analytics,
            summary=(
                f"Observed {analytics.project_count} project reference(s), "
                f"{analytics.knowledge_node_count} knowledge node(s), and "
                f"{analytics.service_count} service reference(s)."
            ),
        )

    def service_discovery(
        self, services: tuple[ServiceRegistryEntryDTO, ...] = ()
    ) -> ServiceDiscoveryReport:
        ids = tuple(service.service_id for service in services)
        duplicates = tuple(sorted({service_id for service_id in ids if ids.count(service_id) > 1}))
        observed = tuple(
            ServiceDiscoveryDTO(
                service_id=service.service_id,
                capability=service.capability,
                owner=service.owner,
                compatibility=service.compatibility,
            )
            for service in sorted(services, key=lambda item: item.service_id)
        )
        return ServiceDiscoveryReport(
            services=observed,
            compatible_service_count=sum(
                service.compatibility in {"v5_additive", "v6_foundation"} for service in services
            ),
            duplicate_service_ids=duplicates,
        )

    def intelligence(
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
        collaboration_workspace_id: str | None = None,
    ) -> CreativeProductionPlatformIntelligenceReport:
        foundation = self._foundation.foundation(
            project_id,
            context,
            projects=projects,
            workspaces=workspaces,
            knowledge=knowledge,
            assignments=assignments,
            services=services,
        )
        graph = self.knowledge_graph(knowledge, knowledge_edges)
        workspace_id = collaboration_workspace_id or (
            workspaces[0].workspace_id if workspaces else f"workspace:{project_id}"
        )
        return CreativeProductionPlatformIntelligenceReport(
            foundation=foundation,
            knowledge_graph=graph,
            context=self.context_engine(project_id, context),
            workflow=self.workflow_orchestrator(project_id, context),
            automation=self.automation_hub(project_id, context, automation_rules),
            collaboration=self.collaboration_workspace(project_id, workspace_id, assignments),
            analytics=self.production_analytics(foundation, graph),
            services=self.service_discovery(services),
        )


def _require_unique(values: Iterable[str], field_name: str) -> None:
    items = tuple(values)
    if len(items) != len(set(items)):
        raise ValueError(f"{field_name} values must be unique")
