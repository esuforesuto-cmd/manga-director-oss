# Migrating to v2.6.0

v2.6.0 is backward compatible with v1.x and v2.0.x-v2.5.x public contracts.
No workflow, configuration, Project-data, Repository, Provider, Image Backend,
Plugin, or Extension SDK migration is required.

1. Install `manga-director==2.6.0` from the approved artifact.
2. Retain existing `config.yaml`, persisted Project files, and database data.
3. Run existing health, repository integrity, workflow validation, and release
   readiness checks in the target environment.
4. Confirm optional extras required by the deployment remain installed.

The v2.6 planning, analysis, governance, and readiness services are advisory;
adopting them does not modify persisted state or workflow execution semantics.
