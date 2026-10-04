# Supervisor Runtime Foundation

The supervisor foundation reports local, non-authoritative execution evidence.
It monitors no live process and has no permission to dispatch, transition,
recover, retry, approve, notify, or persist.

| DTO | Purpose | Disabled boundary |
| --- | --- | --- |
| `SupervisorSessionDTO` | Prepared relationship to one execution session. | Starting or retaining a supervisor session. |
| `ProgressMonitorDTO` | Local checkpoint count and zero-progress projection. | Active monitoring and telemetry export. |
| `HealthStatusDTO` | Initial health/failure diagnostic state. | Remediation or durable health records. |
| `EscalationDTO` | Human-decision-required escalation packet. | Sending escalation or triggering emergency stop. |

Supervisor output is advisory evidence only. High-risk or incomplete evidence
must remain visible to a human rather than triggering an automatic response.
