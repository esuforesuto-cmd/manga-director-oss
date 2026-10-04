# Migrating to v3.3.0

`3.3.0` is backward compatible with v1.x, v2.x, v3.0, v3.1, and v3.2 public
contracts. No data, configuration, Repository, workflow, database, or SDK
migration is required.

1. Install the approved stable artifact: `manga-director==3.3.0`.
2. Keep existing workflow execution through the CLI, API, MCP, or Application
   services; the StateMachine remains authoritative.
3. Treat Production, Quality, Asset, Project, and Governance DTOs as advisory
   reports. They cannot enforce policy or perform operational actions.
4. Validate the project with existing repository and workflow checks before
   resuming normal work.
