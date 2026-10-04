# Knowledge Foundation

The Knowledge Foundation derives a bounded index from the existing
`ProjectRepository` interface. `KnowledgeNamespace`, `KnowledgeCategory`,
`KnowledgeTag`, `KnowledgeReference`, `KnowledgeSnapshot`, and
`KnowledgeIndexSummary` are DTOs, not a new persistence model.

Only project identifiers, titles, counts, and metadata *keys* are projected.
Metadata values are not included in references; therefore the report is
redacted by design and `persistence_mutated` is always `false`.

Delivery is available through `manga-director director foundation`,
`GET /v3/knowledge`, and the `knowledge_foundation` MCP tool. Future graph and
semantic retrieval work must continue to use repository ports and add explicit
retention/provenance policy.

See [Knowledge Foundation example](../examples/knowledge_foundation/run.py).
