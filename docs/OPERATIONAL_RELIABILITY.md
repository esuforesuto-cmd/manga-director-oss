# Operational Reliability

## Scope

`operational_reliability()` exposes a diagnostic reliability placeholder above
the v4.8 Operational Insights report. The initial health status is
`not_checked`, making the absence of real health evidence explicit.

## Boundary

The report cannot health-check, detect a failure, monitor, alert, retry,
recover, reconfigure Runtime, persist an incident, or take automatic action.
It preserves exactly-one-Page scope and StateMachine authority, so it cannot
change Workflow safety gates or any existing Runtime contract.
