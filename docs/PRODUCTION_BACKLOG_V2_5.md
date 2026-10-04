# v2.5 Production Backlog

The following are Issue candidates, not approved implementation work. They must
keep Core isolated and preserve StateMachine authority.

| ID | Area | Candidate outcome | Required acceptance evidence |
| --- | --- | --- | --- |
| PROD-01 | Workflow | Repeatable resume/consistency/approval regression fixture. | One-page, storyboard, quality, approval, save/reload/resume tests. |
| PROD-02 | Repository | Large aggregate, bounded history, integrity, and recovery workload record. | Repository-port compatibility, fixture baseline, rollback guidance. |
| PROD-03 | Diagnostics / Observability | Safe report retention/export ownership policy. | Redaction, DTO-only, JSON/Markdown, access/retention documentation. |
| PROD-04 | Health | Readiness/liveness ownership and failure classification. | Mock dependency failure, no network probe, shutdown evidence. |
| PROD-05 | Automation / Notification | Retry and recovery operating runbooks. | Failure isolation, audit evidence, no workflow-state bypass. |
| PROD-06 | Configuration / Logging | Upgrade, fingerprint, secret masking, and log retention procedure. | Compatibility, validation, redaction, rollback fixture. |
| PROD-07 | Recovery / Deployment | Backup-restore exercise and deployment checklist. | Repository integrity before/after, explicit operator decision points. |

No candidate may introduce automatic approval, multi-page generation, direct
Agent invocation from a delivery layer, Cloud control plane, or distributed
runtime.
