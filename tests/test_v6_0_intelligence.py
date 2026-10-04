"""Validation for read-only v6.0 platform intelligence projections."""

from __future__ import annotations

from pathlib import Path

import pytest

from manga_director.domain.state_machine import PageState
from manga_director.production import (
    CollaborationAssignmentDTO,
    KnowledgeCoreReferenceDTO,
    KnowledgeGraphEdgeDTO,
    ProjectHubReferenceDTO,
    ServiceRegistryEntryDTO,
    V60AutomationRuleDTO,
    V60CreativeProductionPlatformIntelligenceService,
    WorkspaceHubReferenceDTO,
)
from manga_director.workflow import WorkflowContext

ROOT = Path(__file__).resolve().parents[1]


def _context() -> WorkflowContext:
    return WorkflowContext(
        page={"id": "volume-1-page-1"},
        state=PageState.QUALITY_CHECKED,
        artifacts={
            PageState.STORYBOARDED.value: {"panels": []},
            PageState.QUALITY_CHECKED.value: {"status": "passed"},
        },
        metadata={
            "story_context": {"beat": "resolution"},
            "character_context": {"hero": "Aki"},
            "world_context": {"location": "station"},
            "timeline_context": {"scene": 8},
        },
    )


def _knowledge() -> tuple[KnowledgeCoreReferenceDTO, ...]:
    return (
        KnowledgeCoreReferenceDTO(
            knowledge_id="character:aki",
            project_id="volume-1",
            kind="character",
            source_reference="character_context",
            provenance="workflow-metadata",
        ),
        KnowledgeCoreReferenceDTO(
            knowledge_id="story:volume-1",
            project_id="volume-1",
            kind="story",
            source_reference="story_context",
            provenance="workflow-metadata",
        ),
    )


def test_knowledge_graph_builds_only_an_in_memory_provenance_projection() -> None:
    report = V60CreativeProductionPlatformIntelligenceService().knowledge_graph(
        _knowledge(),
        (
            KnowledgeGraphEdgeDTO(
                edge_id="story-to-character",
                source_node_id="story:volume-1",
                target_node_id="character:aki",
                relationship="references",
            ),
        ),
    )

    assert tuple(node.node_id for node in report.nodes) == ("character:aki", "story:volume-1")
    assert report.valid is True
    assert report.graph_projection_built is True
    assert report.graph_persisted is False
    assert report.source_repository_changed is False


def test_knowledge_graph_reports_unknown_edges_without_repairing_them() -> None:
    report = V60CreativeProductionPlatformIntelligenceService().knowledge_graph(
        _knowledge(),
        (
            KnowledgeGraphEdgeDTO(
                edge_id="unknown-edge",
                source_node_id="story:volume-1",
                target_node_id="missing",
                relationship="references",
            ),
        ),
    )

    assert report.valid is False
    assert report.findings == ("edge unknown-edge references an unknown node",)


def test_knowledge_graph_rejects_duplicate_edge_identifiers() -> None:
    edge = KnowledgeGraphEdgeDTO(
        edge_id="story-to-character",
        source_node_id="story:volume-1",
        target_node_id="character:aki",
        relationship="references",
    )

    with pytest.raises(ValueError, match="edge_id values must be unique"):
        V60CreativeProductionPlatformIntelligenceService().knowledge_graph(
            _knowledge(),
            (edge, edge),
        )


def test_context_engine_uses_present_context_without_prompt_or_state_change() -> None:
    context = _context()
    before = context.model_dump()

    report = V60CreativeProductionPlatformIntelligenceService().context_engine("volume-1", context)

    assert report.complete is True
    assert tuple(fragment.context_key for fragment in report.fragments) == (
        "story_context",
        "character_context",
        "world_context",
        "timeline_context",
    )
    assert report.context_persisted is False
    assert report.prompt_generated is False
    assert report.workflow_mutated is False
    assert context.model_dump() == before


def test_context_engine_reports_incomplete_context_without_filling_missing_inputs() -> None:
    context = _context().model_copy(
        update={
            "metadata": {
                "story_context": {"beat": "resolution"},
                "world_context": {"location": "station"},
            }
        }
    )
    before = context.model_dump()

    report = V60CreativeProductionPlatformIntelligenceService().context_engine("volume-1", context)

    assert report.complete is False
    assert tuple(fragment.context_key for fragment in report.fragments) == (
        "story_context",
        "world_context",
    )
    assert tuple(fragment.category for fragment in report.fragments) == ("story", "world")
    assert report.context_persisted is False
    assert report.workflow_mutated is False
    assert context.model_dump() == before


def test_workflow_orchestrator_only_recommends_the_state_machine_command() -> None:
    context = _context()
    before = context.model_dump()

    report = V60CreativeProductionPlatformIntelligenceService().workflow_orchestrator("volume-1", context)

    assert report.orchestrator.next_command == "approve"
    assert report.state_machine_authoritative is True
    assert report.orchestrator.execution_dispatched is False
    assert report.orchestrator.workflow_mutated is False
    assert context.model_dump() == before


def test_automation_hub_matches_rules_but_never_dispatches_them() -> None:
    report = V60CreativeProductionPlatformIntelligenceService().automation_hub(
        "volume-1",
        _context(),
        (
            V60AutomationRuleDTO(
                rule_id="recommend-approve",
                event_key="quality-complete",
                recommended_command="approve",
            ),
        ),
    )

    assert report.matching_rule_ids == ("recommend-approve",)
    assert report.valid is True
    assert report.automation_dispatched is False
    assert report.automation_persisted is False


def test_collaboration_workspace_remains_scoped_and_requires_review() -> None:
    report = V60CreativeProductionPlatformIntelligenceService().collaboration_workspace(
        "volume-1",
        "workspace:one",
        (
            CollaborationAssignmentDTO(
                assignment_id="review:one",
                project_id="volume-1",
                workspace_id="workspace:one",
                role="reviewer",
                assignee_reference="editor-1",
            ),
            CollaborationAssignmentDTO(
                assignment_id="review:other",
                project_id="volume-2",
                workspace_id="workspace:two",
                role="reviewer",
                assignee_reference="editor-2",
            ),
        ),
    )

    assert report.workspace.assignment_ids == ("review:one",)
    assert report.all_reviews_required is True
    assert report.collaboration_executed is False
    assert report.approval_granted is False


def test_analytics_and_service_discovery_are_deterministic_and_observational() -> None:
    service = V60CreativeProductionPlatformIntelligenceService()
    report = service.intelligence(
        "volume-1",
        _context(),
        projects=(ProjectHubReferenceDTO(project_id="volume-1", title="One"),),
        workspaces=(
            WorkspaceHubReferenceDTO(
                workspace_id="workspace:one", project_id="volume-1", label="One"
            ),
        ),
        knowledge=_knowledge(),
        services=(
            ServiceRegistryEntryDTO(
                service_id="knowledge-graph",
                capability="provenance-projection",
                owner="knowledge_engine",
                compatibility="v6_foundation",
            ),
        ),
    )

    assert report.analytics.analytics.knowledge_node_count == 2
    assert report.analytics.analytics.quality_review_completed is True
    assert report.analytics.decision_automated is False
    assert report.services.compatible_service_count == 1
    assert report.services.registry_mutated is False


def test_intelligence_composes_all_iteration_two_areas_without_automatic_action() -> None:
    report = V60CreativeProductionPlatformIntelligenceService().intelligence(
        "volume-1",
        _context(),
        projects=(ProjectHubReferenceDTO(project_id="volume-1", title="One"),),
        workspaces=(
            WorkspaceHubReferenceDTO(
                workspace_id="workspace:one", project_id="volume-1", label="One"
            ),
        ),
        knowledge=_knowledge(),
        assignments=(
            CollaborationAssignmentDTO(
                assignment_id="review:one",
                project_id="volume-1",
                workspace_id="workspace:one",
                role="reviewer",
                assignee_reference="editor-1",
            ),
        ),
        services=(
            ServiceRegistryEntryDTO(
                service_id="knowledge-graph",
                capability="provenance-projection",
                owner="knowledge_engine",
                compatibility="v6_foundation",
            ),
        ),
        automation_rules=(
            V60AutomationRuleDTO(
                rule_id="recommend-approve",
                event_key="quality-complete",
                recommended_command="approve",
            ),
        ),
    )

    assert report.v5_compatibility_preserved is True
    assert report.automatic_action_taken is False
    assert report.foundation.production.production.page_count == 1
    assert report.analytics.analytics.assignment_count == 1
    assert report.services.compatible_service_count == 1


def test_intelligence_rejects_multi_page_context() -> None:
    context = _context().model_copy(update={"page": {"pages": [{"id": "one"}, {"id": "two"}]}})

    with pytest.raises(ValueError, match="exactly one Page"):
        V60CreativeProductionPlatformIntelligenceService().context_engine("volume-1", context)


def test_v6_intelligence_keeps_delivery_repository_and_execution_boundaries_out() -> None:
    source = (ROOT / "src/manga_director/production/v6_0_intelligence.py").read_text(
        encoding="utf-8"
    )

    for forbidden in (
        "manga_director.api",
        "manga_director.cli",
        "manga_director.mcp",
        "manga_director.repositories",
        "workflow.engine",
        ".execute(",
        ".advance(",
        "save(",
        ".publish(",
        ".load(",
    ):
        assert forbidden not in source


def test_v6_intelligence_documentation_is_available() -> None:
    documents = (
        "docs/KNOWLEDGE_GRAPH.md",
        "docs/CONTEXT_ENGINE.md",
        "docs/WORKFLOW_ORCHESTRATOR.md",
        "docs/AUTOMATION_HUB.md",
        "docs/COLLABORATION_WORKSPACE.md",
        "docs/PRODUCTION_ANALYTICS.md",
        "docs/SERVICE_DISCOVERY.md",
    )

    assert all((ROOT / document).is_file() for document in documents)
