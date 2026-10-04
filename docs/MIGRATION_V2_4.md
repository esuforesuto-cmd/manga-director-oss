# Migrating to v2.4.0

## Compatibility

No data migration, state migration, command rename, or code change is required
when upgrading from v1.x or a v2.0.x-v2.3.x release. The forward-only page
StateMachine and Repository port remain unchanged.

## Upgrade steps

1. Install the signed-off `manga-director==2.4.0` wheel or sdist.
2. Keep existing `config.yaml`, project files, repository selection, Plugins,
   and Extensions unchanged.
3. Run `manga-director --help`, `health summary`, and a repository check in a
   non-production copy of the project before deployment.
4. Use existing Project, Chapter, Batch, and page resume operations. Do not
   edit persisted workflow state directly.

## Optional production services

Production Runtime, operations, reliability, health, and diagnostics helpers
are additive. Adopt them at the application composition boundary and retain the
existing `Repository` interface. They do not add a workflow REST API, remote
provider execution, Cloud monitoring, or distributed operation.

## Rollback

Because no persisted schema or state contract changes in this release, rolling
back to a supported v2.x release only requires installing the previous package
version. Keep normal project backups and validate repository integrity before
resuming work.
