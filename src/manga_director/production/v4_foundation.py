"""v4 Creative Operating System foundations with no execution authority.

The DTOs in this module derive bounded evidence from the existing Project
Repository and one-page WorkflowContext. They never create or persist a
workspace, memory, graph, snapshot, timeline, or quality result; they do not
execute a workflow, generate content, complete review, or approve a Page.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import Field

from manga_director.domain.project import Project
from manga_director.domain.state_machine import PageState
from manga_director.production.director import DirectorModel
from manga_director.repositories.protocols import ProjectRepository
from manga_director.workflow.contracts import WorkflowContext


class WorkspaceDTO(DirectorModel):
    workspace_id: str
    project_id: str
    page_reference: str
    current_state: PageState
    repository_read_only: bool = True


class WorkspaceSessionDTO(DirectorModel):
    session_id: str
    project_id: str
    page_reference: str
    session_started: bool = False


class WorkspaceSnapshotDTO(DirectorModel):
    snapshot_id: str
    observed_artifact_count: int = Field(ge=0)
    snapshot_persisted: bool = False


class WorkspaceTimelineDTO(DirectorModel):
    observed_event_count: int = Field(ge=0)
    timeline_persisted: bool = False
    workflow_changed: bool = False


class WorkspaceSummary(DirectorModel):
    project_id: str
    observed_reference_count: int = Field(ge=0)
    automatic_action_taken: bool = False


class WorkspaceFoundationReport(DirectorModel):
    workspace: WorkspaceDTO
    session: WorkspaceSessionDTO
    snapshot: WorkspaceSnapshotDTO
    timeline: WorkspaceTimelineDTO
    summary: WorkspaceSummary
    analysis_only: bool = True


class StoryMemoryDTO(DirectorModel):
    memory_id: str
    observed_history_count: int = Field(ge=0)
    memory_persisted: bool = False


class CharacterMemoryDTO(DirectorModel):
    memory_id: str
    observed_reference_count: int = Field(ge=0)
    memory_persisted: bool = False


class WorldMemoryDTO(DirectorModel):
    memory_id: str
    observed_reference_count: int = Field(ge=0)
    memory_persisted: bool = False


class StyleMemoryDTO(DirectorModel):
    memory_id: str
    observed_artifact_count: int = Field(ge=0)
    memory_persisted: bool = False


class ProductionMemoryDTO(DirectorModel):
    memory_id: str
    observed_history_count: int = Field(ge=0)
    memory_persisted: bool = False


class MemoryIndexDTO(DirectorModel):
    index_id: str
    entry_count: int = Field(ge=0)
    index_persisted: bool = False
    remote_lookup_performed: bool = False


class CreativeMemoryReport(DirectorModel):
    story: StoryMemoryDTO
    character: CharacterMemoryDTO
    world: WorldMemoryDTO
    style: StyleMemoryDTO
    production: ProductionMemoryDTO
    index: MemoryIndexDTO
    analysis_only: bool = True


class GraphNodeDTO(DirectorModel):
    node_id: str
    category: str
    source: str = "repository_projection"
    persisted: bool = False


class GraphEdgeDTO(DirectorModel):
    source_id: str
    target_id: str
    relation: str
    persisted: bool = False


class StoryGraphDTO(DirectorModel):
    graph_id: str
    nodes: tuple[GraphNodeDTO, ...] = ()
    edges: tuple[GraphEdgeDTO, ...] = ()
    repository_read_only: bool = True


class CharacterGraphDTO(DirectorModel):
    graph_id: str
    nodes: tuple[GraphNodeDTO, ...] = ()
    edges: tuple[GraphEdgeDTO, ...] = ()
    repository_read_only: bool = True


class GraphSummary(DirectorModel):
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    graph_persisted: bool = False
    automatic_action_taken: bool = False


class CreativeGraphReport(DirectorModel):
    story: StoryGraphDTO
    character: CharacterGraphDTO
    summary: GraphSummary
    analysis_only: bool = True


class StoryQualityDTO(DirectorModel):
    observed_history_count: int = Field(ge=0)
    quality_score_computed: bool = False
    story_changed: bool = False


class CharacterConsistencyDTO(DirectorModel):
    observed_reference_count: int = Field(ge=0)
    consistency_enforced: bool = False
    character_changed: bool = False


class VisualConsistencyDTO(DirectorModel):
    observed_artifact_count: int = Field(ge=0)
    visual_changed: bool = False
    image_generated: bool = False


class EditorialReviewDTO(DirectorModel):
    current_state: PageState
    review_completed: bool = False
    approval_granted: bool = False


class CreativeQualitySummary(DirectorModel):
    project_id: str
    observed_signal_count: int = Field(ge=0)
    quality_enforced: bool = False
    automatic_action_taken: bool = False


class CreativeQualityReport(DirectorModel):
    story: StoryQualityDTO
    character: CharacterConsistencyDTO
    visual: VisualConsistencyDTO
    editorial: EditorialReviewDTO
    summary: CreativeQualitySummary
    analysis_only: bool = True


class CreativeFoundationRepository:
    """Read existing Project evidence without changing the Repository contract."""

    def __init__(self, repository: ProjectRepository) -> None:
        self._repository = repository

    def project(self, project_id: str) -> Project:
        return self._repository.load(project_id)


class V4FoundationService:
    """Build v4 DTO projections without workspace, memory, graph, or quality authority."""

    def __init__(self, repository: ProjectRepository) -> None:
        self._evidence = CreativeFoundationRepository(repository)

    def workspace(self, project_id: str, context: WorkflowContext) -> WorkspaceFoundationReport:
        project = self._evidence.project(project_id)
        page_reference = _page_reference(context)
        history_count = len(_history(context))
        reference_count = len(project.metadata) + len(context.artifacts) + history_count
        return WorkspaceFoundationReport(
            workspace=WorkspaceDTO(
                workspace_id=f"workspace:{project.id}:{page_reference}",
                project_id=project.id,
                page_reference=page_reference,
                current_state=context.state,
            ),
            session=WorkspaceSessionDTO(
                session_id=f"workspace-session:{project.id}:{page_reference}",
                project_id=project.id,
                page_reference=page_reference,
            ),
            snapshot=WorkspaceSnapshotDTO(
                snapshot_id=f"workspace-snapshot:{project.id}:{page_reference}",
                observed_artifact_count=len(context.artifacts),
            ),
            timeline=WorkspaceTimelineDTO(observed_event_count=history_count),
            summary=WorkspaceSummary(
                project_id=project.id, observed_reference_count=reference_count
            ),
        )

    def memory(self, project_id: str, context: WorkflowContext) -> CreativeMemoryReport:
        project = self._evidence.project(project_id)
        page_reference = _page_reference(context)
        history_count = len(_history(context))
        metadata_count = len(project.metadata)
        return CreativeMemoryReport(
            story=StoryMemoryDTO(
                memory_id=f"story-memory:{project.id}:{page_reference}",
                observed_history_count=history_count,
            ),
            character=CharacterMemoryDTO(
                memory_id=f"character-memory:{project.id}:{page_reference}",
                observed_reference_count=metadata_count,
            ),
            world=WorldMemoryDTO(
                memory_id=f"world-memory:{project.id}:{page_reference}",
                observed_reference_count=metadata_count,
            ),
            style=StyleMemoryDTO(
                memory_id=f"style-memory:{project.id}:{page_reference}",
                observed_artifact_count=len(context.artifacts),
            ),
            production=ProductionMemoryDTO(
                memory_id=f"production-memory:{project.id}:{page_reference}",
                observed_history_count=history_count,
            ),
            index=MemoryIndexDTO(
                index_id=f"memory-index:{project.id}:{page_reference}", entry_count=5
            ),
        )

    def graph(self, project_id: str, context: WorkflowContext) -> CreativeGraphReport:
        project = self._evidence.project(project_id)
        page_reference = _page_reference(context)
        story_node = GraphNodeDTO(node_id=f"story:{project.id}", category="story")
        page_node = GraphNodeDTO(node_id=f"page:{project.id}:{page_reference}", category="page")
        character_node = GraphNodeDTO(
            node_id=f"character:{project.id}:{page_reference}", category="character"
        )
        story_edge = GraphEdgeDTO(
            source_id=story_node.node_id, target_id=page_node.node_id, relation="contains"
        )
        character_edge = GraphEdgeDTO(
            source_id=character_node.node_id,
            target_id=page_node.node_id,
            relation="observed_for_page",
        )
        return CreativeGraphReport(
            story=StoryGraphDTO(
                graph_id=f"story-graph:{project.id}:{page_reference}",
                nodes=(story_node, page_node),
                edges=(story_edge,),
            ),
            character=CharacterGraphDTO(
                graph_id=f"character-graph:{project.id}:{page_reference}",
                nodes=(character_node, page_node),
                edges=(character_edge,),
            ),
            summary=GraphSummary(node_count=3, edge_count=2),
        )

    def quality(self, project_id: str, context: WorkflowContext) -> CreativeQualityReport:
        project = self._evidence.project(project_id)
        history_count = len(_history(context))
        metadata_count = len(project.metadata)
        artifact_count = len(context.artifacts)
        return CreativeQualityReport(
            story=StoryQualityDTO(observed_history_count=history_count),
            character=CharacterConsistencyDTO(observed_reference_count=metadata_count),
            visual=VisualConsistencyDTO(observed_artifact_count=artifact_count),
            editorial=EditorialReviewDTO(current_state=context.state),
            summary=CreativeQualitySummary(
                project_id=project.id,
                observed_signal_count=history_count + metadata_count + artifact_count,
            ),
        )


def _page_reference(context: WorkflowContext) -> str:
    value = context.page.get("id")
    return str(value) if value is not None else "page"


def _history(context: WorkflowContext) -> tuple[object, ...]:
    metadata: Mapping[str, object] = context.metadata
    value = metadata.get("workflow_history", ())
    return tuple(value) if isinstance(value, list | tuple) else ()
