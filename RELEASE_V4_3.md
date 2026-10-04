# manga-director v4.3.0

## Release overview

v4.3.0 promotes the RC1-reviewed Creative Production Platform to a stable
release. It adds no functionality beyond RC1 and retains the Core StateMachine,
Workflow Engine, Repository ports, and documented v4.2 public contracts.

## Included platform capabilities

- Production Pipeline, Asset Management, Project Workspace, and Deliverable
  Management DTO projections.
- Production Automation, Asset Intelligence, Publishing Workflow, and Project
  Analytics planning and reporting projections.
- Production Governance, Quality Assurance, Operations Monitoring, and Platform
  Reliability evidence for human review.

All v4.3 capabilities are typed, transport-neutral, exactly-one-Page-scoped,
and non-executing. They cannot transition workflows, assign or dispatch work,
persist a new catalog, export, publish, distribute, approve, enforce policy,
monitor, alert, recover, bill, or call external services.

## Compatibility and migration

v4.3.0 is backward compatible with v4.2 and documented earlier public
contracts. No project, repository, workflow, configuration, or code migration
is required. See the [Migration Guide](docs/MIGRATION_V4_3.md) and
[Compatibility Verification](docs/COMPATIBILITY_V4_3.md).

## Release validation

The final local suite covers regression, architecture, compatibility,
integration, benchmark, package, documentation, and security-boundary checks.
See the [release-ready report](docs/V4_3_RELEASE_READY_REPORT.md) and
[release checklist](docs/RELEASE_CHECKLIST_V4_3.md).

## Known limitations

Automatic production execution, publishing/distribution, approval, policy
enforcement, monitoring, alerting, recovery, external integrations, billing,
Cloud services, marketplace, and distributed runtime remain intentionally out
of scope.
