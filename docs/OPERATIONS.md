# Operations Guide

Use existing delivery commands and DTOs; operations must not edit page state
outside the WorkflowEngine.

1. Validate configuration profile and secret sources before startup.
2. Run `health summary`, `diagnostics report`, `provider check`, and `backend
   check` for local boundary evidence.
3. Run `repository check --project PROJECT_ID` before a manual resume.
4. Resume through Project, Chapter, Batch, or page Workflow APIs only.
5. Export redacted diagnostics for incident review and retain them according to
   the operator's access policy.

v2.4 release operations retain these local, repository-port-based controls.
Remote probes, Cloud monitoring, and distributed execution remain outside this
guide.
