# Security Monitoring and Incident Response

`SecurityMonitoringService` produces a single, read-only snapshot from the
existing audit log, threat findings, and caller-supplied incident status.
`SecurityMonitoringReport` includes only safe identifiers, aggregate audit
counts, and response recommendations.

The service never starts a monitoring loop, polls a service, sends an alert,
creates a ticket, changes a policy, rotates credentials, or remediates an
incident. Each `IncidentResponseRecommendation` explicitly requires human
action and records `response_executed=False`.

Open high- or critical-severity incidents, as well as blocking threat findings,
set `human_response_required`. Incident identifiers are validated using the
existing `SecurityValidator` and must be unique. Incident category, severity,
and status values are also checked at runtime.

For release-readiness checks that compose this snapshot with compliance
controls, see [Security Compliance and Release Validation](SECURITY_COMPLIANCE_RELEASE_VALIDATION.md).
