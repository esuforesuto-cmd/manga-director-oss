# manga-director v4.7.0

## Release overview

v4.7.0 promotes the RC1-reviewed Creative Decision Platform to a stable
release. It adds no functionality beyond RC1 and retains the Core StateMachine,
Workflow Engine, Repository ports, and documented v4.6 public contracts.

## Included Creative Decision capabilities

- Decision Engine and Recommendation Framework review projections.
- Review Intelligence, Approval Platform, and Executive Dashboard projections.
- Decision Intelligence, Recommendation Analytics, Review Analytics, and
  Approval Insights.
- Decision Governance, Recommendation Governance, Review Audit, Approval
  Compliance, and Decision Reliability reports for human review.

All v4.7 capabilities are typed, transport-neutral, exactly-one-page-scoped,
and non-executing. They cannot collect or persist evidence, select a decision
or recommendation, complete review, grant approval, mutate or execute
workflows, enforce policy, monitor, alert, retry, recover, or call external
services.

## Compatibility and migration

v4.7.0 is backward compatible with v4.6 and documented earlier public
contracts. No project, repository, workflow, configuration, or code migration
is required. See the [Migration Guide](docs/MIGRATION_V4_7.md) and
[Compatibility Verification](docs/COMPATIBILITY_V4_7.md).

## Release validation

The final local suite covers regression, architecture, compatibility, Decision
Platform integration, benchmark, package, documentation, security, and Web UI
checks. See the [release-ready report](docs/V4_7_RELEASE_READY_REPORT.md) and
[release checklist](docs/RELEASE_CHECKLIST_V4_7.md).

## Known limitations

Evidence persistence, policy enforcement, autonomous decision or execution,
recommendation selection, review completion, approval, workflow mutation,
telemetry, monitoring, recovery, external integrations, Cloud services, and
distributed runtime remain intentionally out of scope.
