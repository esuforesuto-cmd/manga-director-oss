# Migrating to v3.2.0

`3.2.0` is backward compatible with v1.x, v2.x, v3.0, and v3.1 public
contracts. No workflow, Repository, database, or configuration migration is
required.

1. Install `manga-director==3.2.0` from the approved release artifact.
2. Keep existing Project files, plugins, extensions, provider/backend settings,
   and one-Page workflow commands unchanged.
3. Treat v3.2 CLI, FastAPI, MCP, and Web UI entries as optional diagnostic DTO
   views; they do not execute a workflow or grant approval.

The stable release adds no autonomous AI, Agent execution, deployment, or
release action.
