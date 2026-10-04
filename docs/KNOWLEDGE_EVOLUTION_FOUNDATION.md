# Knowledge Evolution Foundation

The v3.1 Knowledge Evolution foundation is a bounded, read-only projection of
the existing `ProjectRepository`. It provides a version marker, redacted
snapshot, structural diff, timeline, evolution report, and history summary.

Only project identifiers, titles, counts, timestamps, and metadata **keys** are
projected. Metadata values are deliberately excluded. No version is persisted,
merged, or used to change a Project.

## Delivery

- CLI: `manga-director director knowledge-evolution`
- FastAPI: `GET /v3.1/knowledge-evolution`
- MCP: `knowledge_evolution`

Future versioning, merging, retention, and conflict handling require separate
Repository-port design and explicit human authorization. See the
[example](../examples/knowledge_evolution/run.py).
