"""Read-only v6.1 metadata diagnostics for caller-supplied Knowledge Graph nodes.

This opt-in service augments an existing v6.0 graph projection with immutable
metadata descriptors. It neither changes provenance nor persists, reviews, or
executes any production state.
"""

from __future__ import annotations

from typing import Literal

from manga_director.production.director import DirectorModel
from manga_director.production.v6_0_intelligence import KnowledgeGraphReport


class KnowledgeGraphMetadataDescriptorDTO(DirectorModel):
    """Caller-supplied advisory metadata for one existing Knowledge Graph node."""

    node_id: str
    confidence_label: str = ""
    retention_classification: str = ""
    retention_policy_reference: Literal["human_retention_decision"] = "human_retention_decision"
    redaction_label: str = ""
    review_required: Literal[True] = True
    review_reference: str = ""


class KnowledgeMetadataCompletenessDTO(DirectorModel):
    """Diagnostic result for one graph node or an unknown descriptor target."""

    node_id: str
    complete: bool
    missing_fields: tuple[str, ...] = ()
    findings: tuple[str, ...] = ()


class KnowledgeGraphMetadataReport(DirectorModel):
    """Immutable advisory report; it is not a graph, policy, or review action."""

    descriptors: tuple[KnowledgeGraphMetadataDescriptorDTO, ...] = ()
    completeness: tuple[KnowledgeMetadataCompletenessDTO, ...] = ()
    valid: bool
    findings: tuple[str, ...] = ()
    metadata_projection_built: Literal[True] = True
    metadata_persisted: Literal[False] = False
    source_repository_changed: Literal[False] = False
    review_executed: Literal[False] = False
    approval_granted: Literal[False] = False
    analysis_only: Literal[True] = True


class V61KnowledgeGraphMetadataService:
    """Validate metadata presence for an existing graph without changing v6.0 behavior."""

    def metadata_report(
        self,
        graph: KnowledgeGraphReport,
        descriptors: tuple[KnowledgeGraphMetadataDescriptorDTO, ...] = (),
    ) -> KnowledgeGraphMetadataReport:
        """Return a deterministic, immutable diagnostic for caller-supplied descriptors."""

        _require_unique_descriptor_node_ids(descriptors)
        ordered_descriptors = tuple(sorted(descriptors, key=lambda item: item.node_id))
        by_node_id = {descriptor.node_id: descriptor for descriptor in ordered_descriptors}
        known_node_ids = tuple(sorted(node.node_id for node in graph.nodes))
        known_node_id_set = set(known_node_ids)

        completeness = tuple(
            _known_node_completeness(node_id, by_node_id.get(node_id)) for node_id in known_node_ids
        ) + tuple(
            _unknown_node_completeness(node_id)
            for node_id in sorted(set(by_node_id).difference(known_node_id_set))
        )
        findings = tuple(
            finding for diagnostic in completeness for finding in diagnostic.findings
        )
        return KnowledgeGraphMetadataReport(
            descriptors=ordered_descriptors,
            completeness=completeness,
            valid=not findings,
            findings=findings,
        )


def _require_unique_descriptor_node_ids(
    descriptors: tuple[KnowledgeGraphMetadataDescriptorDTO, ...],
) -> None:
    node_ids = tuple(descriptor.node_id for descriptor in descriptors)
    if len(node_ids) != len(set(node_ids)):
        raise ValueError("metadata descriptor node_id values must be unique")


def _known_node_completeness(
    node_id: str, descriptor: KnowledgeGraphMetadataDescriptorDTO | None
) -> KnowledgeMetadataCompletenessDTO:
    if descriptor is None:
        finding = f"graph node {node_id} has no metadata descriptor"
        return KnowledgeMetadataCompletenessDTO(
            node_id=node_id,
            complete=False,
            missing_fields=("descriptor",),
            findings=(finding,),
        )

    missing_fields = tuple(
        field_name
        for field_name, value in (
            ("confidence_label", descriptor.confidence_label),
            ("retention_classification", descriptor.retention_classification),
            ("redaction_label", descriptor.redaction_label),
            ("review_reference", descriptor.review_reference),
        )
        if not value
    )
    findings = (
        (f"metadata descriptor for graph node {node_id} is missing required fields",)
        if missing_fields
        else ()
    )
    return KnowledgeMetadataCompletenessDTO(
        node_id=node_id,
        complete=not missing_fields,
        missing_fields=missing_fields,
        findings=findings,
    )


def _unknown_node_completeness(node_id: str) -> KnowledgeMetadataCompletenessDTO:
    finding = f"metadata descriptor references an unknown graph node {node_id}"
    return KnowledgeMetadataCompletenessDTO(
        node_id=node_id,
        complete=False,
        findings=(finding,),
    )
