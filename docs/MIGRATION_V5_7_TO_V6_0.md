# Migration Strategy: v5.7 to v6.0

## Stable adoption status

v6.0.0 is an additive, opt-in stable release. Upgrade with
`manga-director==6.0.0` to evaluate its read-only Platform Kernel reports.
No data migration, configuration change, endpoint change, CLI change, MCP
change, Web UI change, Repository migration, Plugin migration, or workflow
migration is required.

## Future adoption rules

1. New v6 capabilities must be opt-in and additive.
2. Existing v5.x Python API, CLI, FastAPI/REST, MCP, Web UI, Repository,
   Workflow, SDK, Plugin, and StateMachine contracts remain available.
3. Workspace, collaboration, knowledge, and automation records reference
   source-owned data; they do not replace it.
4. Existing one-page workflow rules continue to govern generation and approval.

## Rollback

Every v6 addition can be removed by stopping use of its opt-in service. Reinstall
`manga-director==5.7.0` to return to the compatibility baseline; no persisted
v6 data format is introduced.
