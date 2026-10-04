# Upgrade Manager Foundation

`UpgradeManagerFoundation` evaluates an `UpgradePlanDTO` for a human upgrade decision. The DTO records source and target versions, owner, v5.0 LTS compatibility evidence, migration notes, and a rollback reference.

The Foundation returns `ready`, `needs_review`, or `blocked` evidence. It never invokes a package manager, edits configuration, runs a migration, performs rollback, or changes runtime state. Existing CLI, API, MCP, Web UI, repository, workflow, and SDK contracts remain optional consumers of the report.
