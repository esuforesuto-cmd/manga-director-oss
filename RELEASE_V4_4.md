# manga-director v4.4.0

## Release overview

v4.4.0 promotes the RC1-reviewed Enterprise Creative Platform to a stable
release. It adds no functionality beyond RC1 and retains the Core StateMachine,
Workflow Engine, Repository ports, and documented v4.3 public contracts.

## Included platform capabilities

- Enterprise Workspace, Team Collaboration, Portfolio Management, Extension
  Registry, and Marketplace Catalog DTO projections.
- Collaboration Intelligence, Portfolio Analytics, Extension Intelligence,
  Marketplace Insights, and an Enterprise Dashboard for supplied evidence.
- Enterprise Governance, Workspace Compliance, Portfolio Governance,
  Marketplace Governance, and Enterprise Reliability evidence for human review.

All v4.4 capabilities are typed, transport-neutral, exactly-one-Page-scoped,
and non-executing. They cannot transition workflows, change membership,
allocate capacity, persist enterprise state, discover/install/load/execute
extensions, operate a marketplace, approve, enforce policy, monitor, alert,
recover, bill, or call external services.

## Compatibility and migration

v4.4.0 is backward compatible with v4.3 and documented earlier public
contracts. No project, repository, workflow, configuration, or code migration
is required. See the [Migration Guide](docs/MIGRATION_V4_4.md) and
[Compatibility Verification](docs/COMPATIBILITY_V4_4.md).

## Release validation

The final local suite covers regression, architecture, compatibility,
Enterprise integration, benchmark, package, documentation, and security
boundary checks. See the [release-ready report](docs/V4_4_RELEASE_READY_REPORT.md)
and [release checklist](docs/RELEASE_CHECKLIST_V4_4.md).

## Known limitations

Enterprise persistence, identity/access enforcement, collaboration messaging,
marketplace operation, extension execution, policy enforcement, monitoring,
recovery, external integrations, billing, Cloud services, and distributed
runtime remain intentionally out of scope.
