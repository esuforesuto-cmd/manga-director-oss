# manga-director v4.5.0

## Release overview

v4.5.0 promotes the RC1-reviewed Creative Intelligence Ecosystem to a stable
release. It adds no functionality beyond RC1 and retains the Core StateMachine,
Workflow Engine, Repository ports, and documented v4.4 public contracts.

## Included ecosystem capabilities

- Creative Service Registry, Service Intelligence, and Service Trust Framework
  review projections.
- Plugin Foundation, Plugin Analytics, and Plugin Governance projections that
  preserve the existing Plugin and Extension SDK contracts.
- Workflow Marketplace Foundation and Workflow Insights for local,
  exactly-one-page supplied evidence.
- Knowledge Exchange and Federation Registry foundation, analytics, and
  governance evidence.
- Ecosystem Dashboard, Governance, and Reliability reports for human review.

All v4.5 capabilities are typed, transport-neutral, exactly-one-page-scoped,
and non-executing. They cannot transition workflows, register or invoke a
service, load or execute a plugin, operate a marketplace, synchronize
knowledge, connect a federation, enforce policy, approve, monitor, retry,
recover, persist ecosystem state, bill, or call external services.

## Compatibility and migration

v4.5.0 is backward compatible with v4.4 and documented earlier public
contracts. No project, repository, workflow, configuration, or code migration
is required. See the [Migration Guide](docs/MIGRATION_V4_5.md) and
[Compatibility Verification](docs/COMPATIBILITY_V4_5.md).

## Release validation

The final local suite covers regression, architecture, compatibility, Ecosystem
integration, benchmark, package, documentation, and security-boundary checks.
See the [release-ready report](docs/V4_5_RELEASE_READY_REPORT.md) and
[release checklist](docs/RELEASE_CHECKLIST_V4_5.md).

## Known limitations

Service invocation, plugin loading/execution, marketplace operation, knowledge
synchronization, federation networking, policy enforcement, monitoring,
recovery, external integrations, billing, Cloud services, and distributed
runtime remain intentionally out of scope.
