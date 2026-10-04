# manga-director v4.6.0

## Release overview

v4.6.0 promotes the RC1-reviewed Creative Intelligence OS to a stable release.
It adds no functionality beyond RC1 and retains the Core StateMachine, Workflow
Engine, Repository ports, and documented v4.5 public contracts.

## Included Creative Intelligence capabilities

- Unified Creative Context and Cross-Agent Memory reference projections.
- Creative Reasoning and Adaptive Workflow analysis projections.
- Intelligence Hub composition and dashboard projections.
- Intelligence Governance, Context Governance, Reasoning Audit, Workflow
  Observability, and Intelligence Reliability reports for human review.

All v4.6 capabilities are typed, transport-neutral, exactly-one-page-scoped,
and non-executing. They cannot collect or persist context, read/write/share
memory, update a model, learn, decide autonomously, invoke agents, mutate or
execute workflows, enforce policy, approve, monitor, alert, retry, recover, or
call external services.

## Compatibility and migration

v4.6.0 is backward compatible with v4.5 and documented earlier public
contracts. No project, repository, workflow, configuration, or code migration
is required. See the [Migration Guide](docs/MIGRATION_V4_6.md) and
[Compatibility Verification](docs/COMPATIBILITY_V4_6.md).

## Release validation

The final local suite covers regression, architecture, compatibility, Creative
Intelligence integration, benchmark, package, documentation, and security
boundary checks. See the [release-ready report](docs/V4_6_RELEASE_READY_REPORT.md)
and [release checklist](docs/RELEASE_CHECKLIST_V4_6.md).

## Known limitations

Context persistence, shared memory, model updates, self-learning, autonomous
decision or execution, workflow mutation, telemetry, monitoring, recovery,
external integrations, Cloud services, and distributed runtime remain
intentionally out of scope.
