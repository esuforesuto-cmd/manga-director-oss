# Migrating from v3.5 to v4.0.0

v4.0.0 is backward compatible with documented v3.5 public contracts. Install
`manga-director==4.0.0` and retain existing projects, repositories, workflow
configurations, Providers, Backends, Plugins, Extensions, automation, and
notification settings.

No schema, database, Repository, configuration, or workflow migration is
required. Creative Workspace, Memory, Graph, Quality, Intelligence, and
Governance are optional DTO-only reports. They do not authorize policy
enforcement, stage transitions, Page approval, image generation, monitoring,
deployment, or publication.

For a production upgrade, run configuration validation, Repository integrity,
health, diagnostics, and a human-reviewed one-page workflow smoke test before
promotion. See the [Release Checklist](RELEASE_CHECKLIST_V4.md).
