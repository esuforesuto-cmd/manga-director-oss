# Migrating to v2.5.0

## Scope

v2.5.0 is backward compatible with v1.x and v2.0.x-v2.4.x public contracts.
No workflow, configuration, Project-data, Provider, Image Backend, Plugin, or
Extension SDK migration is required.

## Upgrade steps

1. Install `manga-director==2.5.0` from the approved release artifact.
2. Retain existing `config.yaml` and persisted Project files or database data.
3. Run the existing test, health, repository integrity, and release-readiness
   checks in the target environment.
4. Confirm any optional extras required by your deployment remain installed.

## Validation

Use the read-only `ReleaseReadiness` and Repository health reports before
production use. They do not repair or modify data. Rollback remains a normal
package/environment rollback because persisted aggregate semantics are unchanged.
