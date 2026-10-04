"""Contracts for opt-in v6.1 bounded Knowledge Graph traversal."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.production import (
    KnowledgeCoreReferenceDTO,
    KnowledgeGraphEdgeDTO,
    KnowledgeGraphMetadataDescriptorDTO,
    V60CreativeProductionPlatformIntelligenceService,
    V61KnowledgeGraphMetadataService,
    V61KnowledgeGraphTraversalService,
)

ROOT = Path(__file__).resolve().parents[1]


def _graph(edges: tuple[KnowledgeGraphEdgeDTO, ...] = ()):
    references = tuple(
        KnowledgeCoreReferenceDTO(
            knowledge_id=knowledge_id,
            project_id="volume-1",
            kind=kind,
            source_reference=f"{kind}_context",
            provenance="workflow-metadata",
        )
        for knowledge_id, kind in (
            ("story:root", "story"),
            ("character:aki", "character"),
            ("world:city", "world"),
            ("asset:station", "asset"),
            ("review:editor", "review"),
        )
    )
    return V60CreativeProductionPlatformIntelligenceService().knowledge_graph(references, edges)


def _edge(edge_id: str, source: str, target: str) -> KnowledgeGraphEdgeDTO:
    return KnowledgeGraphEdgeDTO(
        edge_id=edge_id,
        source_node_id=source,
        target_node_id=target,
        relationship="references",
    )


def test_traversal_returns_an_outgoing_breadth_first_snapshot() -> None:
    report = V61KnowledgeGraphTraversalService().traverse(
        _graph(
            (
                _edge("edge:03:character-asset", "character:aki", "asset:station"),
                _edge("edge:02:root-world", "story:root", "world:city"),
                _edge("edge:01:root-character", "story:root", "character:aki"),
            )
        ),
        "story:root",
        max_depth=2,
    )

    assert tuple((item.node.node_id, item.depth) for item in report.nodes) == (
        ("story:root", 0),
        ("character:aki", 1),
        ("world:city", 1),
        ("asset:station", 2),
    )
    assert tuple(edge.edge_id for edge in report.edges) == (
        "edge:01:root-character",
        "edge:02:root-world",
        "edge:03:character-asset",
    )
    assert report.valid is True
    assert report.truncated is False


def test_traversal_is_outgoing_only() -> None:
    report = V61KnowledgeGraphTraversalService().traverse(
        _graph((_edge("edge:incoming", "character:aki", "story:root"),)), "story:root"
    )

    assert tuple(item.node.node_id for item in report.nodes) == ("story:root",)
    assert report.edges == ()


def test_unknown_root_is_an_advisory_diagnostic() -> None:
    report = V61KnowledgeGraphTraversalService().traverse(_graph(), "story:missing")

    assert report.root_found is False
    assert report.nodes == ()
    assert report.edges == ()
    assert report.valid is False
    assert report.findings == ("traversal root references an unknown graph node story:missing",)


def test_depth_zero_returns_only_the_root_and_reports_normal_truncation() -> None:
    report = V61KnowledgeGraphTraversalService().traverse(
        _graph((_edge("edge:root-character", "story:root", "character:aki"),)),
        "story:root",
        max_depth=0,
    )

    assert tuple((item.node.node_id, item.depth) for item in report.nodes) == (("story:root", 0),)
    assert report.edges == ()
    assert report.valid is True
    assert report.truncated is True
    assert report.truncation_reasons == ("max_depth",)


def test_node_and_edge_limits_are_valid_truncation_with_canonical_reasons() -> None:
    report = V61KnowledgeGraphTraversalService().traverse(
        _graph(
            (
                _edge("edge:01:root-character", "story:root", "character:aki"),
                _edge("edge:02:root-world", "story:root", "world:city"),
                _edge("edge:03:character-root", "character:aki", "story:root"),
                _edge("edge:04:character-asset", "character:aki", "asset:station"),
            )
        ),
        "story:root",
        max_depth=2,
        node_limit=2,
        edge_limit=2,
    )

    assert tuple(item.node.node_id for item in report.nodes) == ("story:root", "character:aki")
    assert tuple(edge.edge_id for edge in report.edges) == (
        "edge:01:root-character",
        "edge:03:character-root",
    )
    assert report.valid is True
    assert report.truncated is True
    assert report.truncation_reasons == ("node_limit", "edge_limit")


def test_edge_limit_bounds_returned_directed_edges() -> None:
    report = V61KnowledgeGraphTraversalService().traverse(
        _graph(
            (
                _edge("edge:02:root-world", "story:root", "world:city"),
                _edge("edge:01:root-character", "story:root", "character:aki"),
            )
        ),
        "story:root",
        edge_limit=1,
    )

    assert tuple(item.node.node_id for item in report.nodes) == ("story:root", "character:aki")
    assert tuple(edge.edge_id for edge in report.edges) == ("edge:01:root-character",)
    assert report.truncation_reasons == ("edge_limit",)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"max_depth": -1}, "max_depth"),
        ({"node_limit": 0}, "node_limit"),
        ({"edge_limit": 0}, "edge_limit"),
    ],
)
def test_traversal_rejects_invalid_bounds(kwargs: dict[str, int], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        V61KnowledgeGraphTraversalService().traverse(_graph(), "story:root", **kwargs)


def test_cycles_do_not_revisit_nodes_and_can_return_a_cycle_edge_once() -> None:
    report = V61KnowledgeGraphTraversalService().traverse(
        _graph(
            (
                _edge("edge:root-character", "story:root", "character:aki"),
                _edge("edge:character-root", "character:aki", "story:root"),
            )
        ),
        "story:root",
        max_depth=2,
    )

    assert tuple(item.node.node_id for item in report.nodes) == ("story:root", "character:aki")
    assert tuple(edge.edge_id for edge in report.edges) == (
        "edge:character-root",
        "edge:root-character",
    )
    assert report.truncated is False


def test_existing_unknown_edge_findings_are_propagated_without_new_validation() -> None:
    graph = _graph((_edge("edge:unknown", "story:root", "world:missing"),))

    report = V61KnowledgeGraphTraversalService().traverse(graph, "story:root")

    assert graph.valid is False
    assert report.valid is False
    assert report.findings == graph.findings
    assert report.edges == ()


def test_traversal_preserves_graph_and_returned_snapshot_immutability() -> None:
    graph = _graph((_edge("edge:root-character", "story:root", "character:aki"),))
    before = graph.model_dump()
    report = V61KnowledgeGraphTraversalService().traverse(graph, "story:root")
    replacement = graph.nodes[0].model_copy(update={"provenance": "changed"})

    assert graph.model_dump() == before
    assert replacement.provenance == "changed"
    assert report.nodes[0].node.provenance == "workflow-metadata"
    with pytest.raises(ValidationError):
        report.root_found = False


def test_traversal_is_independent_from_the_metadata_contract() -> None:
    graph = _graph()
    metadata = V61KnowledgeGraphMetadataService().metadata_report(
        graph,
        (
            KnowledgeGraphMetadataDescriptorDTO(
                node_id="story:root",
                confidence_label="editor-reviewed",
                retention_classification="project-record",
                redaction_label="internal",
                review_reference="review:volume-1",
            ),
        ),
    )
    traversal = V61KnowledgeGraphTraversalService().traverse(graph, "story:root")

    assert metadata.descriptors[0].node_id == traversal.root_node_id
    assert traversal.nodes[0].node.node_id == "story:root"


def test_traversal_keeps_repository_delivery_and_execution_boundaries_out() -> None:
    source = (ROOT / "src/manga_director/production/v6_1_knowledge_traversal.py").read_text(
        encoding="utf-8"
    )

    for forbidden in (
        "manga_director.api",
        "manga_director.cli",
        "manga_director.mcp",
        "manga_director.repositories",
        "manga_director.workflow",
        "manga_director.domain.state_machine",
        "manga_director.providers",
        ".execute(",
        ".advance(",
        "save(",
        ".publish(",
        ".load(",
    ):
        assert forbidden not in source
