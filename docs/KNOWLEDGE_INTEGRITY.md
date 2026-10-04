# Knowledge Integrity

Knowledge Integrity validates repository-derived Creative Knowledge evidence.
It provides integrity, coverage, lifecycle, quality, governance, and risk DTOs
without changing the `ProjectRepository` interface or creating a new store.

The service uses identifiers and metadata keys only. It never exposes metadata
values, persists a projection, or automatically remediates an integrity risk.

Delivery: `manga-director director knowledge-integrity`, `GET
/v3/knowledge-integrity`, and the `knowledge_integrity` MCP tool.
