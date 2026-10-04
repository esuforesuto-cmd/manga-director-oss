# Enterprise Reliability

`V44EnterpriseGovernanceService.enterprise_reliability(project_id, context)`
returns a diagnostic reliability DTO and summary over Enterprise Dashboard
evidence. Its default health is `not_checked`; it does not start monitoring.

Health checks, incident detection, alert delivery, retry, recovery, restoration,
remediation, scheduling, and external operations are disabled. The report is a
planning aid, not a reliability runtime.
