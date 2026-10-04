# Upgrade Policy

## Supported upgrade path

v2.5 planning keeps v1.x and v2.0.x-v2.4.x public contracts compatible unless
a separately approved major-version proposal says otherwise. Patch and minor
releases must preserve the one-page workflow, persisted project state, base
Repository interface, root API, CLI, MCP, Plugin, Extension SDK, Provider, and
Image Backend contracts.

## Before upgrade

1. Read the release notes and migration guide.
2. Back up project storage and record a redacted configuration snapshot.
3. Run configuration validation and repository integrity checks in a copy of
   the target environment.
4. Verify the package version, optional extras, Plugin manifests, and Extension
   minimum-core requirements.

## During and after upgrade

Install only the reviewed artifact, run `manga-director --help`, health, and
repository checks, then resume through normal workflow operations. Roll back by
reinstalling the previous supported package only after validating storage and
operator-owned recovery evidence.

## Policy boundary

No automatic persistent-state rewrite, secret migration, workflow-state repair,
or provider/backend network migration is authorized by this policy.
