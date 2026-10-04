# GitHub Release Notes - v4.7.0

## Creative Decision Platform

v4.7.0 is the stable release of the additive Creative Decision Platform. It
promotes the RC1-reviewed Decision, Recommendation, Review, Approval,
Dashboard, Governance, Audit, Compliance, and Reliability DTO projections
without adding runtime automation.

## Highlights

- Human-governed, exactly-one-page-scoped Decision, Recommendation, Review,
  Approval, Dashboard, Governance, Audit, Compliance, and Reliability evidence.
- Read-only decision analysis and executive dashboard composition.
- Advisory policy, compliance, audit, and reliability reports.
- No change to StateMachine authority or existing v4.6 public contracts.

## Upgrade

No migration is required from v4.6. Install `manga-director==4.7.0`.
See the [Migration Guide](MIGRATION_V4_7.md) and
[Release Ready Report](V4_7_RELEASE_READY_REPORT.md).

## Validation

The local release suite passed regression, compatibility, Decision Platform
end-to-end, benchmark, security-boundary, package, documentation, lint, type,
and Web UI validation. Maintainers must complete exact-tag CI, signing, hosted
scans, and registry publication before publishing this text as a GitHub release.
