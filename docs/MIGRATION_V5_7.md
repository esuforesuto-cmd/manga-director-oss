# Migration Guide: v5.6 to v5.7

## Upgrade

Upgrade normally to `manga-director==5.7.0`. No data migration, configuration
change, endpoint change, CLI migration, MCP migration, Web UI migration,
repository conversion, or Plugin migration is required.

## Optional adoption

Callers may opt in to the frozen Platform, Plugin, and Workspace report APIs by
supplying existing single-page `WorkflowContext` evidence. The reports remain
read-only and optional; omitting them preserves v5.6 behavior.

## Rollback

Stop calling the optional v5.7 report services and install the prior compatible
v5.6 release. No persisted v5.7 data format is introduced.
