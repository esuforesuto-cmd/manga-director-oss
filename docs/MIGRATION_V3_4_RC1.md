# Migrating to v3.4.0 RC1

`3.4.0rc1` is backward compatible with v1.x, v2.x, v3.0, v3.1, v3.2, and v3.3
public contracts. No data, configuration, Repository, workflow, database, or
SDK migration is required.

1. Install the approved prerelease artifact: `manga-director==3.4.0rc1`.
2. Keep workflow execution through the existing CLI, API, MCP, or Application
   services; the StateMachine remains authoritative.
3. Treat v3.4 Knowledge, Operations, Organization, Release, and Governance
   DTOs as advisory reports. They cannot enforce policy or take operational action.
4. Validate the Project with existing repository and workflow checks before
   resuming normal work.
