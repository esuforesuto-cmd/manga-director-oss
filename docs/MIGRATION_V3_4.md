# Migrating to v3.4.0

v3.4.0 is backward compatible with documented v1.x through v3.3.x public
contracts. Install `manga-director==3.4.0` and retain existing projects,
repositories, workflow configurations, Providers, Backends, Plugins,
Extensions, automation, and notification settings.

No schema, database, repository, configuration, or workflow migration is
required. The v3.4 Knowledge, Operations, Organization, Release, and Governance
surfaces are optional diagnostics. They do not authorize deployment, policy
enforcement, stage transitions, Page approval, or image generation.

For a production upgrade, run configuration validation, repository integrity,
health, diagnostics, and a human-reviewed one-Page workflow smoke test before
promotion. See [Release Checklist](RELEASE_CHECKLIST_V3_4.md).
