# Migrating from v1 to v2.3

The v1 public API remains available: `Director`, `WorkflowEngine`,
`WorkflowContext`, `WorkflowResult`, `Project`, `Chapter`, `Page`,
`Repository`, `ImageGenerator`, and Agent contracts.

File repositories need no migration. To adopt SQL persistence, configure
`database_provider` and `database_url`, run the Alembic initial migration, and
import projects through the existing Project serializer. Database, security,
notification, and SDK integrations are additive; they do not loosen page state
transitions or human approval requirements.

No migration is required from v2.0, v2.1, or v2.2 to v2.3. The v2.3 release preserves
the same public workflow, CLI, MCP, repository, Plugin, and Extension SDK
contracts. Verify optional delivery adapters and extension packaging in your
target environment before production use.
