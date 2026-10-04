# Release Readiness Dashboard

`ReleaseReadinessDashboardDTO` combines Quality Intelligence, Review Analytics,
Validation Intelligence, and supplied monitoring snapshots into a single
transport-neutral decision packet. Its readiness value is advisory:
`ready_for_human_decision` still requires authorized human release action.

When human sign-off is required by policy, an explicit satisfied `approval`
criterion with an evidence reference is also required. The dashboard cannot
sign, tag, upload, publish, or operate a release process.
