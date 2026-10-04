# Production Readiness Backlog

v2.4 production work is Issue planning, not an authorization to change Core.
Every item must retain the one-page, forward-only workflow and use existing
ports and DTOs.

| Area | Candidate Issue | Evidence before implementation |
| --- | --- | --- |
| Workflow | PROD-01 interrupted-process recovery matrix | StateMachine, persistence, and explicit approval regression fixtures |
| Repository | PROD-02 large-project backup/recovery guide | integrity/self-check, restore, and rollback rehearsal |
| Automation | PROD-03 execution recovery policy | idempotency, failure isolation, and audit evidence |
| Notification | PROD-04 retry/redaction operations | transient failure fixtures and safe logs |
| Database | PROD-05 PostgreSQL workload/recovery study | query, transaction, migration, and failure-injection baseline |
| Configuration | PROD-06 schema migration dry-run policy | compatibility, fingerprint, redaction, and rollback evidence |
| Security | PROD-07 production hardening review | secret, input/output, rate-limit, audit, and dependency evidence |
| Diagnostics | PROD-08 incident report/export runbook | safe DTO export and retention/access criteria |
| Health | PROD-09 component-health operating model | local probe behavior, timeout/failure policy, no workflow coupling |
| Logging | PROD-10 structured logging policy | level, redaction, correlation, and retention guidance |
