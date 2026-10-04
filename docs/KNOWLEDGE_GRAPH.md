# Knowledge Graph

## v6.0 Iteration 2 foundation

`V60CreativeProductionPlatformIntelligenceService.knowledge_graph()` builds a
bounded, in-memory projection from caller-supplied provenance-bearing
knowledge references and explicit edges. Nodes cover story, character, world,
asset, production, and review evidence.

The projection is diagnostic only: it does not persist nodes or edges, load a
repository, merge records, alter source knowledge, or perform graph traversal
outside the supplied inputs. Edges that reference unknown nodes are returned
as findings for human correction.

```python
from manga_director.production import (
    KnowledgeCoreReferenceDTO,
    KnowledgeGraphEdgeDTO,
    V60CreativeProductionPlatformIntelligenceService,
)

report = V60CreativeProductionPlatformIntelligenceService().knowledge_graph(
    (
        KnowledgeCoreReferenceDTO(
            knowledge_id="story:volume-1",
            project_id="volume-1",
            kind="story",
            source_reference="story_context",
            provenance="workflow-metadata",
        ),
    ),
    (),
)
```

Node and edge identifiers are deterministic public inputs; duplicate
identifiers are rejected rather than merged or repaired.

## v6.1 metadata descriptor contract

`V61KnowledgeGraphMetadataService.metadata_report()` adds an opt-in,
caller-supplied, node-only metadata diagnostic to an existing v6.0 graph
projection. It reports opaque confidence, retention-classification, and
redaction labels together with the existing `human_retention_decision` policy
reference and an explicit human-review reference.

Descriptors are ordered by node identifier, are immutable, and never duplicate
the node's existing provenance. Missing descriptors, missing required metadata,
unknown node references, and duplicate descriptor targets are diagnostic or
validation results; nothing is merged, repaired, retained, redacted, reviewed,
or persisted. Edge metadata and graph traversal remain outside this contract.

## v6.1 bounded traversal read model

`V61KnowledgeGraphTraversalService.traverse()` observes an existing,
caller-supplied v6.0 graph from one required root node. It follows outgoing
edges with deterministic breadth-first ordering. The root is depth zero; the
defaults are `max_depth=1`, `node_limit=50`, and `edge_limit=50`.

Bounds return valid advisory truncation for a valid source graph, with explicit
reasons rather than errors. Unknown roots are diagnostic, and existing unknown
edge findings are propagated without revalidation. Traversal is node-only and
independent of metadata descriptors; it never queries, persists, mutates,
loads, executes, or transitions a workflow.

## Compatibility

The graph is additive to v5.x. Existing Knowledge APIs, repositories,
workflows, CLI, FastAPI, MCP, and Web UI remain unchanged.
