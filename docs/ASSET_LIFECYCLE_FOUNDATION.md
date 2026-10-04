# Asset Lifecycle Foundation

v3.3 Asset Lifecycle uses the existing Repository port to project bounded asset
lifecycle, version, history, archive-eligibility, dependency, and summary DTOs
for one existing Page. It neither changes the Repository interface nor creates
a mutable lifecycle store.

The projection is read-only: it does not persist versions or dependencies,
archive or delete assets, repair history, fetch remotely, or expose metadata
values. Ownership, retention, and archive decisions remain human and
Repository-policy concerns.

Use `manga-director director asset-lifecycle-v33 --project <id> --page
<number>`, the optional `/v3.3/asset-lifecycle` FastAPI provider, or the
`asset_lifecycle_v33` MCP tool.
