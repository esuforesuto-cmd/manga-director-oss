# Migrating to v3.5.0

v3.5.0 is backward compatible with documented v1.x through v3.4.x public
contracts. Install `manga-director==3.5.0` and retain existing projects,
repositories, workflow configurations, Providers, Backends, Plugins,
Extensions, automation, and notification settings.

No schema, database, Repository, configuration, or workflow migration is
required. Unified Knowledge Graph, Creative Intelligence, Production
Intelligence, Platform Analytics, and Governance are optional DTO-only
diagnostics. They do not authorize policy enforcement, stage transitions, Page
approval, image generation, monitoring, deployment, or publication.

For a production upgrade, run configuration validation, Repository integrity,
health, diagnostics, and a human-reviewed one-Page workflow smoke test before
promotion. See the [Release Checklist](RELEASE_CHECKLIST_V3_5.md).
