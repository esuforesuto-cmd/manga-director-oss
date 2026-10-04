# Decision Reliability

Decision Reliability is a diagnostic-only view over the Executive Decision
Dashboard. It exposes a stable no-side-effect reliability contract for
enterprise review.

## Scope

- Health starts as `not_checked`.
- No health check, monitoring, alerting, retry, recovery, or remediation runs.
- The dashboard composition remains presentation-neutral and one-page scoped.

## Boundary

Runtime monitoring, incident detection, persistence, retry, recovery, workflow
action, Cloud operations, and distributed execution are intentionally deferred.
