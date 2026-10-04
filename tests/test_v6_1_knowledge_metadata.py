"""Contracts for opt-in v6.1 Knowledge Graph metadata diagnostics."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from manga_director.production import (
    KnowledgeCoreReferenceDTO,
    KnowledgeGraphMetadataDescriptorDTO,
    V60CreativeProductionPlatformIntelligenceService,
    V61KnowledgeGraphMetadataService,
)

ROOT = Path(__file__).resolve().parents[1]


def _graph():
    return V60CreativeProductionPlatformIntelligenceService().knowledge_graph(
        (
            KnowledgeCoreReferenceDTO(
                knowledge_id="story:volume-1",
                project_id="volume-1",
                kind="story",
                source_reference="story_context",
                provenance="workflow-metadata",
            ),
            KnowledgeCoreReferenceDTO(
                knowledge_id="character:aki",
                project_id="volume-1",
                kind="character",
                source_reference="character_context",
                provenance="character-bible",
            ),
        )
    )


def _descriptor(node_id: str) -> KnowledgeGraphMetadataDescriptorDTO:
    return KnowledgeGraphMetadataDescriptorDTO(
        node_id=node_id,
        confidence_label="editor-reviewed",
        retention_classification="project-record",
        redaction_label="internal",
        review_reference="review:volume-1",
    )


def test_metadata_report_is_complete_deterministic_and_read_only() -> None:
    report = V61KnowledgeGraphMetadataService().metadata_report(
        _graph(),
        (_descriptor("story:volume-1"), _descriptor("character:aki")),
    )

    assert tuple(descriptor.node_id for descriptor in report.descriptors) == (
        "character:aki",
        "story:volume-1",
    )
    assert tuple(diagnostic.node_id for diagnostic in report.completeness) == (
        "character:aki",
        "story:volume-1",
    )
    assert report.valid is True
    assert report.findings == ()
    assert report.metadata_persisted is False
    assert report.source_repository_changed is False
    assert report.review_executed is False
    assert report.approval_granted is False
    assert report.analysis_only is True


def test_metadata_report_diagnoses_graph_nodes_without_descriptors() -> None:
    report = V61KnowledgeGraphMetadataService().metadata_report(
        _graph(), (_descriptor("character:aki"),)
    )

    story = report.completeness[1]
    assert story.node_id == "story:volume-1"
    assert story.complete is False
    assert story.missing_fields == ("descriptor",)
    assert story.findings == ("graph node story:volume-1 has no metadata descriptor",)
    assert report.valid is False


def test_metadata_report_diagnoses_missing_required_metadata_fields() -> None:
    report = V61KnowledgeGraphMetadataService().metadata_report(
        _graph(),
        (
            _descriptor("character:aki"),
            KnowledgeGraphMetadataDescriptorDTO(node_id="story:volume-1"),
        ),
    )

    story = report.completeness[1]
    assert story.complete is False
    assert story.missing_fields == (
        "confidence_label",
        "retention_classification",
        "redaction_label",
        "review_reference",
    )
    assert report.valid is False


def test_metadata_report_diagnoses_unknown_node_references_without_repair() -> None:
    report = V61KnowledgeGraphMetadataService().metadata_report(
        _graph(),
        (
            _descriptor("character:aki"),
            _descriptor("story:volume-1"),
            _descriptor("world:missing"),
        ),
    )

    unknown = report.completeness[-1]
    assert unknown.node_id == "world:missing"
    assert unknown.complete is False
    assert unknown.findings == ("metadata descriptor references an unknown graph node world:missing",)
    assert report.valid is False


def test_metadata_report_rejects_duplicate_descriptor_targets() -> None:
    descriptor = _descriptor("story:volume-1")

    with pytest.raises(ValueError, match="metadata descriptor node_id values must be unique"):
        V61KnowledgeGraphMetadataService().metadata_report(_graph(), (descriptor, descriptor))


def test_descriptor_reuses_retention_and_human_review_contracts() -> None:
    descriptor = _descriptor("story:volume-1")

    assert descriptor.retention_policy_reference == "human_retention_decision"
    assert descriptor.review_required is True
    with pytest.raises(ValidationError):
        KnowledgeGraphMetadataDescriptorDTO(
            node_id="story:volume-1", retention_policy_reference="automatic_retention"
        )
    with pytest.raises(ValidationError):
        KnowledgeGraphMetadataDescriptorDTO(node_id="story:volume-1", review_required=False)


def test_metadata_does_not_duplicate_existing_node_provenance() -> None:
    graph = _graph()
    report = V61KnowledgeGraphMetadataService().metadata_report(
        graph, (_descriptor("character:aki"), _descriptor("story:volume-1"))
    )

    assert graph.nodes[0].provenance == "character-bible"
    assert "provenance" not in KnowledgeGraphMetadataDescriptorDTO.model_fields
    assert report.valid is True


def test_metadata_report_preserves_input_and_returned_snapshot_immutability() -> None:
    descriptors = (_descriptor("story:volume-1"), _descriptor("character:aki"))
    before = tuple(descriptor.model_dump() for descriptor in descriptors)
    report = V61KnowledgeGraphMetadataService().metadata_report(_graph(), descriptors)
    replacement = descriptors[0].model_copy(update={"confidence_label": "changed"})

    assert tuple(descriptor.model_dump() for descriptor in descriptors) == before
    assert replacement.confidence_label == "changed"
    assert report.descriptors[1].confidence_label == "editor-reviewed"
    with pytest.raises(ValidationError):
        report.valid = False


def test_metadata_service_keeps_repository_delivery_and_execution_boundaries_out() -> None:
    source = (ROOT / "src/manga_director/production/v6_1_knowledge_metadata.py").read_text(
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
