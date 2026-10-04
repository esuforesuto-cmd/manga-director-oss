# Migrating to v3.0.0

v3.0.0 is backward compatible with v1.x and v2.0.x-v2.7.x public contracts. No
workflow, configuration, Project-data, Repository, Knowledge, Provider, Image
Backend, Plugin, or Extension SDK migration is required.

1. Install `manga-director==3.0.0` from the approved artifact.
2. Retain existing `config.yaml`, persisted Project files, and database data.
3. Run health, repository integrity, workflow validation, and release readiness
   checks in the target environment.
4. Adopt v3 Director, Creative, Knowledge, Multi-Agent, Review, and readiness
   reports only when their advisory evidence is useful.

v3.0.0 does not introduce autonomous AI, Agent execution, deployment, or
release-authorization behavior.
