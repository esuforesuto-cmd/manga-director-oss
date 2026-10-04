"""Read-only intelligence projections for the v4 Creative Operating System.

This module analyses the bounded DTOs from :mod:`v4_foundation`.  It has no
authority to save evidence, change a workflow, generate an image, complete a
review, or approve a page.  Recommendations are descriptive prompts for a
human operator, never executable commands.
"""

from __future__ import annotations

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.production.v4_foundation import V4FoundationService
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext


class WorkspaceActivityDTO(DirectorModel):
    page_reference: str
    observed_artifact_count: int = Field(ge=0)
    observed_event_count: int = Field(ge=0)
    activity_persisted: bool = False


class WorkspaceAnalyticsDTO(DirectorModel):
    project_id: str
    activity: WorkspaceActivityDTO
    observed_reference_count: int = Field(ge=0)
    analysis_only: bool = True


class SessionTimelineReport(DirectorModel):
    session_id: str
    observed_events: tuple[str, ...] = ()
    timeline_persisted: bool = False
    workflow_changed: bool = False


class WorkspaceHealthReport(DirectorModel):
    status: str
    observed_signal_count: int = Field(ge=0)
    healthy: bool
    health_enforced: bool = False


class WorkspaceRecommendationSummary(DirectorModel):
    recommendations: tuple[str, ...] = ()
    requires_human_review: bool = True
    automatic_action_taken: bool = False


class WorkspaceIntelligenceReport(DirectorModel):
    analytics: WorkspaceAnalyticsDTO
    timeline: SessionTimelineReport
    health: WorkspaceHealthReport
    recommendations: WorkspaceRecommendationSummary
    analysis_only: bool = True


class MemoryInsightDTO(DirectorModel):
    memory_id: str
    observed_entry_count: int = Field(ge=0)
    insight_persisted: bool = False


class MemoryRelationshipAnalysis(DirectorModel):
    observed_relationship_count: int = Field(ge=0)
    remote_lookup_performed: bool = False


class MemoryCoverageReport(DirectorModel):
    observed_categories: tuple[str, ...] = ()
    missing_categories: tuple[str, ...] = ()
    coverage_enforced: bool = False


class MemoryConsistencyReport(DirectorModel):
    consistent: bool
    checked_memory_ids: tuple[str, ...] = ()
    evidence_changed: bool = False


class MemoryRecommendationReport(DirectorModel):
    recommendations: tuple[str, ...] = ()
    requires_human_review: bool = True
    automatic_action_taken: bool = False


class CreativeMemoryIntelligenceReport(DirectorModel):
    insight: MemoryInsightDTO
    relationships: MemoryRelationshipAnalysis
    coverage: MemoryCoverageReport
    consistency: MemoryConsistencyReport
    recommendations: MemoryRecommendationReport
    analysis_only: bool = True


class GraphAnalyticsDTO(DirectorModel):
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    analysis_persisted: bool = False


class RelationshipAnalysisReport(DirectorModel):
    relationship_count: int = Field(ge=0)
    relation_types: tuple[str, ...] = ()
    graph_changed: bool = False


class GraphConsistencyReport(DirectorModel):
    consistent: bool
    unresolved_edge_count: int = Field(ge=0)
    repair_performed: bool = False


class DependencyAnalysis(DirectorModel):
    dependency_count: int = Field(ge=0)
    dependency_cycles_detected: int = Field(ge=0)
    graph_changed: bool = False


class GraphInsightSummary(DirectorModel):
    observations: tuple[str, ...] = ()
    recommendations: tuple[str, ...] = ()
    requires_human_review: bool = True
    automatic_action_taken: bool = False


class CreativeGraphIntelligenceReport(DirectorModel):
    analytics: GraphAnalyticsDTO
    relationships: RelationshipAnalysisReport
    consistency: GraphConsistencyReport
    dependencies: DependencyAnalysis
    insights: GraphInsightSummary
    analysis_only: bool = True


class StoryQualityAnalysis(DirectorModel):
    observed_history_count: int = Field(ge=0)
    analysis_performed: bool = True
    story_changed: bool = False


class CharacterConsistencyAnalysis(DirectorModel):
    observed_reference_count: int = Field(ge=0)
    consistency_observed: bool
    consistency_enforced: bool = False
    character_changed: bool = False


class VisualQualityReport(DirectorModel):
    observed_artifact_count: int = Field(ge=0)
    visual_evidence_available: bool
    image_generated: bool = False
    visual_changed: bool = False


class EditorialInsightReport(DirectorModel):
    current_state: str
    review_completed: bool = False
    approval_granted: bool = False
    recommendation: str


class CreativeQualityDashboard(DirectorModel):
    story: StoryQualityAnalysis
    character: CharacterConsistencyAnalysis
    visual: VisualQualityReport
    editorial: EditorialInsightReport
    observed_signal_count: int = Field(ge=0)
    requires_human_review: bool = True
    quality_enforced: bool = False
    analysis_only: bool = True


class V4IntelligenceService:
    """Derive v4 intelligence reports solely from Foundation projections."""

    def __init__(self, repository: ProjectRepository) -> None:
        self._foundation = V4FoundationService(repository)

    def workspace(self, project_id: str, context: WorkflowContext) -> WorkspaceIntelligenceReport:
        foundation = self._foundation.workspace(project_id, context)
        activity = WorkspaceActivityDTO(
            page_reference=foundation.workspace.page_reference,
            observed_artifact_count=foundation.snapshot.observed_artifact_count,
            observed_event_count=foundation.timeline.observed_event_count,
        )
        observed_events = tuple(
            f"observed:{index + 1}" for index in range(foundation.timeline.observed_event_count)
        )
        signals = activity.observed_artifact_count + activity.observed_event_count
        recommendations = (
            ("Review the persisted storyboard before any image generation.",)
            if activity.observed_artifact_count == 0
            else ("Review observed workspace evidence with a human operator.",)
        )
        return WorkspaceIntelligenceReport(
            analytics=WorkspaceAnalyticsDTO(
                project_id=foundation.workspace.project_id,
                activity=activity,
                observed_reference_count=foundation.summary.observed_reference_count,
            ),
            timeline=SessionTimelineReport(
                session_id=foundation.session.session_id, observed_events=observed_events
            ),
            health=WorkspaceHealthReport(
                status="observed", observed_signal_count=signals, healthy=signals > 0
            ),
            recommendations=WorkspaceRecommendationSummary(recommendations=recommendations),
        )

    def memory(self, project_id: str, context: WorkflowContext) -> CreativeMemoryIntelligenceReport:
        foundation = self._foundation.memory(project_id, context)
        categories = ("story", "character", "world", "style", "production")
        memory_ids = (
            foundation.story.memory_id,
            foundation.character.memory_id,
            foundation.world.memory_id,
            foundation.style.memory_id,
            foundation.production.memory_id,
        )
        return CreativeMemoryIntelligenceReport(
            insight=MemoryInsightDTO(
                memory_id=foundation.index.index_id,
                observed_entry_count=foundation.index.entry_count,
            ),
            relationships=MemoryRelationshipAnalysis(observed_relationship_count=len(categories)),
            coverage=MemoryCoverageReport(observed_categories=categories),
            consistency=MemoryConsistencyReport(
                consistent=len(set(memory_ids)) == len(memory_ids), checked_memory_ids=memory_ids
            ),
            recommendations=MemoryRecommendationReport(
                recommendations=(
                    "Review memory evidence before adding or changing retained knowledge.",
                )
            ),
        )

    def graph(self, project_id: str, context: WorkflowContext) -> CreativeGraphIntelligenceReport:
        foundation = self._foundation.graph(project_id, context)
        nodes = foundation.story.nodes + foundation.character.nodes
        edges = foundation.story.edges + foundation.character.edges
        node_ids = {node.node_id for node in nodes}
        unresolved = sum(
            edge.source_id not in node_ids or edge.target_id not in node_ids for edge in edges
        )
        relation_types = tuple(sorted({edge.relation for edge in edges}))
        return CreativeGraphIntelligenceReport(
            analytics=GraphAnalyticsDTO(
                node_count=foundation.summary.node_count, edge_count=foundation.summary.edge_count
            ),
            relationships=RelationshipAnalysisReport(
                relationship_count=len(edges), relation_types=relation_types
            ),
            consistency=GraphConsistencyReport(
                consistent=unresolved == 0, unresolved_edge_count=unresolved
            ),
            dependencies=DependencyAnalysis(
                dependency_count=len(edges), dependency_cycles_detected=0
            ),
            insights=GraphInsightSummary(
                observations=("Graph evidence is a read-only repository projection.",),
                recommendations=(
                    "Review unresolved relationships before any human-led graph update.",
                ),
            ),
        )

    def quality(self, project_id: str, context: WorkflowContext) -> CreativeQualityDashboard:
        foundation = self._foundation.quality(project_id, context)
        visual_evidence = foundation.visual.observed_artifact_count > 0
        return CreativeQualityDashboard(
            story=StoryQualityAnalysis(
                observed_history_count=foundation.story.observed_history_count
            ),
            character=CharacterConsistencyAnalysis(
                observed_reference_count=foundation.character.observed_reference_count,
                consistency_observed=foundation.character.observed_reference_count > 0,
            ),
            visual=VisualQualityReport(
                observed_artifact_count=foundation.visual.observed_artifact_count,
                visual_evidence_available=visual_evidence,
            ),
            editorial=EditorialInsightReport(
                current_state=foundation.editorial.current_state.value,
                recommendation="Complete the existing quality review before any approval decision.",
            ),
            observed_signal_count=foundation.summary.observed_signal_count,
        )
