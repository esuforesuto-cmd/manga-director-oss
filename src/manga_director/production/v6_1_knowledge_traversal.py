"""Read-only, bounded v6.1 traversal for caller-supplied Knowledge Graph reports.

The service observes a v6.0 graph projection without loading a repository,
modifying graph evidence, or executing production behavior.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from manga_director.production.director import DirectorModel
from manga_director.production.v6_0_intelligence import (
    KnowledgeGraphEdgeDTO,
    KnowledgeGraphNodeDTO,
    KnowledgeGraphReport,
)

TraversalTruncationReason = Literal["max_depth", "node_limit", "edge_limit"]
_TRUNCATION_REASON_ORDER: tuple[TraversalTruncationReason, ...] = (
    "max_depth",
    "node_limit",
    "edge_limit",
)


class KnowledgeGraphTraversalNodeDTO(DirectorModel):
    """A returned graph node with its read-model hop distance from the root."""

    node: KnowledgeGraphNodeDTO
    depth: int = Field(ge=0)


class KnowledgeGraphTraversalLimitsDTO(DirectorModel):
    """Explicit bounds for a local, in-memory traversal read model."""

    max_depth: int = Field(default=1, ge=0)
    node_limit: int = Field(default=50, ge=1)
    edge_limit: int = Field(default=50, ge=1)


class KnowledgeGraphTraversalReport(DirectorModel):
    """Frozen traversal snapshot with advisory source findings and truncation state."""

    root_node_id: str
    root_found: bool
    nodes: tuple[KnowledgeGraphTraversalNodeDTO, ...] = ()
    edges: tuple[KnowledgeGraphEdgeDTO, ...] = ()
    limits: KnowledgeGraphTraversalLimitsDTO
    valid: bool
    findings: tuple[str, ...] = ()
    truncated: bool = False
    truncation_reasons: tuple[TraversalTruncationReason, ...] = ()
    traversal_read_model_built: Literal[True] = True
    traversal_persisted: Literal[False] = False
    repository_queried: Literal[False] = False
    workflow_executed: Literal[False] = False
    state_machine_transitioned: Literal[False] = False
    analysis_only: Literal[True] = True


class V61KnowledgeGraphTraversalService:
    """Traverse existing directed graph evidence without operational authority."""

    def traverse(
        self,
        graph: KnowledgeGraphReport,
        root_node_id: str,
        *,
        max_depth: int = 1,
        node_limit: int = 50,
        edge_limit: int = 50,
    ) -> KnowledgeGraphTraversalReport:
        """Return a deterministic outgoing breadth-first snapshot within explicit bounds."""

        _validate_limits(max_depth=max_depth, node_limit=node_limit, edge_limit=edge_limit)
        limits = KnowledgeGraphTraversalLimitsDTO(
            max_depth=max_depth,
            node_limit=node_limit,
            edge_limit=edge_limit,
        )
        nodes_by_id = {node.node_id: node for node in graph.nodes}
        root = nodes_by_id.get(root_node_id)
        if root is None:
            finding = f"traversal root references an unknown graph node {root_node_id}"
            return KnowledgeGraphTraversalReport(
                root_node_id=root_node_id,
                root_found=False,
                limits=limits,
                valid=False,
                findings=graph.findings + (finding,),
            )

        outgoing = _outgoing_edges(graph.edges, nodes_by_id)
        depths: dict[str, int] = {root.node_id: 0}
        frontier: tuple[str, ...] = (root.node_id,)
        traversed_edges: list[KnowledgeGraphEdgeDTO] = []
        reasons: set[TraversalTruncationReason] = set()

        while frontier:
            next_frontier: set[str] = set()
            for node_id in sorted(frontier):
                depth = depths[node_id]
                candidates = outgoing.get(node_id, ())
                if depth >= max_depth:
                    if candidates:
                        reasons.add("max_depth")
                    continue

                for edge in candidates:
                    if len(traversed_edges) >= edge_limit:
                        reasons.add("edge_limit")
                        continue
                    target_node_id = edge.target_node_id
                    if target_node_id not in depths and len(depths) >= node_limit:
                        reasons.add("node_limit")
                        continue
                    traversed_edges.append(edge)
                    if target_node_id not in depths:
                        depths[target_node_id] = depth + 1
                        next_frontier.add(target_node_id)
            frontier = tuple(sorted(next_frontier))

        ordered_nodes = tuple(
            KnowledgeGraphTraversalNodeDTO(node=nodes_by_id[node_id], depth=depth)
            for node_id, depth in sorted(depths.items(), key=lambda item: (item[1], item[0]))
        )
        ordered_edges = tuple(sorted(traversed_edges, key=lambda edge: edge.edge_id))
        ordered_reasons_list: list[TraversalTruncationReason] = [
            reason for reason in _TRUNCATION_REASON_ORDER if reason in reasons
        ]
        ordered_reasons = tuple(ordered_reasons_list)
        return KnowledgeGraphTraversalReport(
            root_node_id=root_node_id,
            root_found=True,
            nodes=ordered_nodes,
            edges=ordered_edges,
            limits=limits,
            valid=graph.valid,
            findings=graph.findings,
            truncated=bool(ordered_reasons),
            truncation_reasons=ordered_reasons,
        )


def _validate_limits(*, max_depth: int, node_limit: int, edge_limit: int) -> None:
    if max_depth < 0:
        raise ValueError("max_depth must be non-negative")
    if node_limit < 1:
        raise ValueError("node_limit must be at least 1")
    if edge_limit < 1:
        raise ValueError("edge_limit must be at least 1")


def _outgoing_edges(
    edges: tuple[KnowledgeGraphEdgeDTO, ...],
    nodes_by_id: dict[str, KnowledgeGraphNodeDTO],
) -> dict[str, tuple[KnowledgeGraphEdgeDTO, ...]]:
    outgoing: dict[str, list[KnowledgeGraphEdgeDTO]] = {}
    for edge in sorted(edges, key=lambda item: item.edge_id):
        if edge.source_node_id in nodes_by_id and edge.target_node_id in nodes_by_id:
            outgoing.setdefault(edge.source_node_id, []).append(edge)
    return {node_id: tuple(node_edges) for node_id, node_edges in outgoing.items()}
