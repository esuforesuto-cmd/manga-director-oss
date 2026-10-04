# Security Audit and Threat Validation

`SecurityAuditValidator` reads the existing in-memory `AuditLogger` and
validates caller-supplied `SecurityThreatFinding` records. The validator returns
only aggregate event counts, authorization-denial counts, threat identifiers,
and blocking status; it does not expose audit metadata or secret values.

High- and critical-severity findings block validation until they are marked as
mitigated. A missing audit trail is also reported as not valid. Validation is
read-only: it does not remediate findings, alter authorization policy, execute a
workflow, mutate project state, or persist audit data.

Threat identifiers are validated through the existing `SecurityValidator` and
must be unique. Threat category and severity values are also checked at runtime.
Evidence references must identify safe policy, test, or audit locations rather
than contain credentials or raw payloads.
