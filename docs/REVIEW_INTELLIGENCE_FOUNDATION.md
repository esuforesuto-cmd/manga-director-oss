# Review Intelligence Foundation

`V47DecisionFoundationService.review_intelligence()` exposes a transport-neutral
Review Intelligence DTO over supplied Decision and Recommendation evidence. It
describes finding count, coverage and consistency readiness, escalation, and
approval-recommendation flags without performing a review.

The service cannot generate or change content, mutate a finding, mark review
complete, approve a page, bypass a quality gate, execute a workflow, persist a
report, collect telemetry, or notify an external service.
