# Migration Guide: v5.7 to v6.0

## Upgrade

Upgrade to `manga-director==6.0.0`. No data migration, configuration change,
endpoint change, CLI migration, MCP migration, Web UI migration, Repository
conversion, SDK migration, Plugin migration, or workflow migration is
required.

## Optional adoption

Callers may opt in to v6.0 Platform Kernel reports by supplying existing,
single-Page `WorkflowContext` evidence and immutable DTO descriptors. The
reports are read-only and optional; omitting them preserves v5.7 behavior.

## Rollback

Stop calling optional v6.0 report services and install `manga-director==5.7.0`.
No persisted v6.0 data format is introduced.
