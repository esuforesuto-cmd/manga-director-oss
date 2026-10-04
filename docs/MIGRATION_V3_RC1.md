# Migrating to v3.0.0 RC1

`3.0.0rc1` is backward compatible with v1.x and v2.x public contracts. No
workflow, configuration, Project-data, Repository, Provider, Image Backend,
Plugin, or Extension SDK migration is required.

1. Install `manga-director==3.0.0rc1` from the approved prerelease artifact.
2. Retain existing `config.yaml`, persisted Project files, and database data.
3. Run existing health, repository-integrity, workflow-validation, and release
   readiness checks in the target environment.
4. Adopt Director, Creative, Knowledge, Multi-Agent, Review, and readiness
   services only when their advisory reports are useful; none changes execution.

The RC does not introduce autonomous AI, Agent execution, deployment, or
release-authorization behavior.
