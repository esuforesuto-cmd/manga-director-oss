# Knowledge Platform Foundation

v3.4 adds a read-only Knowledge Platform projection in the Knowledge-facing
Application layer. `V34FoundationService.knowledge_platform()` returns catalog,
relationship, classification, quality, index, summary, and dashboard DTOs for
one existing Page through the existing `ProjectRepository` port.

The service reports counts and identifiers only; it never exposes metadata
values. It does not persist an index or relationship, search remotely, write,
merge, repair, archive, delete, modify a `WorkflowContext`, or replace the
Repository interface.

Use `manga-director director knowledge-platform-v34 --project <id> --page
<number>`, the optional `/v3.4/knowledge-platform` FastAPI provider, or the
`knowledge_platform_v34` MCP tool.
