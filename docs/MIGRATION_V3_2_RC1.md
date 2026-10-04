# Migrating to v3.2.0 RC1

`3.2.0rc1` is backward compatible with v1.x, v2.x, v3.0, and v3.1 public
contracts. No workflow migration, Repository migration, or configuration
migration is required.

1. Install `manga-director==3.2.0rc1` from the approved prerelease artifact.
2. Keep existing Project files, plugins, extensions, provider/backend settings,
   and one-Page workflow commands unchanged.
3. Treat new v3.2 CLI, FastAPI, and MCP entries as optional diagnostic DTO
   views; they do not execute a workflow or grant approval.

The RC adds no autonomous AI, Agent execution, deployment, or release action.
