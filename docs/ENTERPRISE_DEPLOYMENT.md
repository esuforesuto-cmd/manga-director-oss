# Enterprise Deployment Guide

## Scope

This guide covers v2.4.0's local, repository-port-based deployment model. It
does not authorize cloud control planes, distributed workflow, or external
credential storage in `config.yaml`.

## Configuration

Select a configuration profile (`development`, `testing`, `production`,
`enterprise`, or `offline`) in the Configuration Layer. Store credentials in
environment variables or a Secret Provider boundary, never in project files.
Use configuration snapshots, diffs, governance reports, and read-only mode for
change review.

## Persistence and recovery

Choose a repository through configuration; application and workflow code must
depend only on `ProjectRepository`. Before resuming an interrupted project,
run `manga-director repository check --project PROJECT_ID`. Preserve backups of
the persisted project data and use normal project/batch resume paths rather
than modifying workflow state manually.

## Runtime operations

Use `health summary`, `provider check`, `backend check`, `diagnostics report`,
and `diagnostics export` for safe, local evidence. These commands do not issue
provider requests or generate images. Health and diagnostics output is safe for
operational review but should still follow local retention and access policy.

## Extension governance

Install only reviewed local Plugins and Extensions. Validate manifests,
compatibility, and declared dependencies before enabling them. Isolate an
unhealthy extension/plugin by disabling it rather than altering Core workflow
rules.

## Release controls

Use the release checklist, SBOM, dependency license report, supported-version
policy, security policy, and hosted CI results before promoting an artifact.
